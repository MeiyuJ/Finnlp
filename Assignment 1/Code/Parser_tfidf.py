import os
import re
import numpy as np
import pandas as pd
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import MOD_Load_MasterDictionary_v2023 as LM

# === Configuration ===
INPUT_DIR = r'C:\Users\Admin\Desktop\Assignment 1\EDGAR_Data\\'
OUTPUT_FILE = r'C:\Users\Admin\Desktop\Assignment 1\result\tfidf_output.csv'
FINNEG_DICT_PATH = r'C:\Users\Admin\Desktop\Assignment 1\Code\dictionary\Loughran-McDonald_MasterDictionary_1993-2023.csv'
HARVARD_NEG_PATH = r'C:\Users\Admin\Desktop\Assignment 1\Code\dictionary\Harvard IV_Negative Word List_Inf.txt'

# === Load Word Lists ===
def load_dictionaries():
    print("Loading Fin-Neg dictionary...")
    lm_dict = LM.load_masterdictionary(FINNEG_DICT_PATH)
    fin_neg_words = {w for w, v in lm_dict.items() if v.negative}

    print("Loading Harvard Negative word list...")
    with open(HARVARD_NEG_PATH, 'r') as f:
        harvard_neg_words = {line.strip().upper() for line in f if line.strip()}

    return fin_neg_words, harvard_neg_words


# === Collect all .txt files recursively ===
def collect_files(input_dir):
    files = []
    for root, dirs, filenames in os.walk(INPUT_DIR):
        for fname in filenames:
            if fname.endswith('.txt'):
                files.append(os.path.join(root, fname))
    
    return files


# === Worker function to process one file ===
def process_file(args):
    path, fin_index, h4n_index = args
    V_fin = len(fin_index)
    V_h4n = len(h4n_index)
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read().upper()
        tokens = re.findall(r'\w+', text)
        doc_len = len(tokens)

        tf_fin = np.zeros(V_fin)
        tf_h4n = np.zeros(V_h4n)
        idf_fin = np.zeros(V_fin)
        idf_h4n = np.zeros(V_h4n)

        seen_fin = set()
        seen_h4n = set()

        for token in tokens:
            if token in fin_index:
                idx = fin_index[token]
                tf_fin[idx] += 1
                seen_fin.add(idx)
            if token in h4n_index:
                idx = h4n_index[token]
                tf_h4n[idx] += 1
                seen_h4n.add(idx)

        for idx in seen_fin:
            idf_fin[idx] = 1
        for idx in seen_h4n:
            idf_h4n[idx] = 1

        return (os.path.basename(path), tf_fin, tf_h4n, idf_fin, idf_h4n, doc_len)
    except Exception as e:
        print(f"Error in {path}: {e}")
        return None

def main():
    # === Load word lists ===
    fin_neg_words, harvard_neg_words = load_dictionaries()

    # === Create word-to-index maps ===
    fin_index = {w: i for i, w in enumerate(fin_neg_words)}
    h4n_index = {w: i for i, w in enumerate(harvard_neg_words)}
    V_fin = len(fin_index)
    V_h4n = len(h4n_index)

    # === Collect files ===
    files = collect_files(INPUT_DIR)
    N = len(files)
    print(f"Found {N} documents.")

    # === Prepare tasks
    tasks = [(path, fin_index, h4n_index) for path in files]

    # === Process files in parallel
    print(f"Processing files with {cpu_count()} cores...")
    with Pool(cpu_count()) as pool:
        results = list(tqdm(pool.imap(process_file, tasks), total=len(tasks)))

    # === Filter out failed cases
    results = [r for r in results if r is not None]
    if not results:
        print("❌ No files processed successfully.")
        return

    # === Unpack results
    file_names, tf_fins, tf_h4ns, idf_fins, idf_h4ns, doc_lengths = zip(*results)
    tf_fins = np.stack(tf_fins)
    tf_h4ns = np.stack(tf_h4ns)
    idf_fins = np.stack(idf_fins)
    idf_h4ns = np.stack(idf_h4ns)
    doc_lengths = np.array(doc_lengths)
    N = len(doc_lengths)
    print(f"Processed {N} documents.")

    # === Compute IDF weights
    print("Computing IDF weights...")
    df_fin = np.sum(idf_fins, axis=0) + 1
    df_h4n = np.sum(idf_h4ns, axis=0) + 1
    idf_weights_fin = np.log(N / df_fin)
    idf_weights_h4n = np.log(N / df_h4n)

    # === Compute TF-IDF
    print("Computing TF-IDF matrix...")
    tfidf_fin = (tf_fins / doc_lengths[:, None]) * idf_weights_fin
    tfidf_h4n = (tf_h4ns / doc_lengths[:, None]) * idf_weights_h4n

    avg_tfidf_fin = np.mean(tfidf_fin, axis=1)
    avg_tfidf_h4n = np.mean(tfidf_h4n, axis=1)

    # === Export
    print("Saving output...")
    df_out = pd.DataFrame({
        'file': file_names,
        'avg_tfidf_finneg': avg_tfidf_fin,
        'avg_tfidf_h4n': avg_tfidf_h4n,
        'doc_length': doc_lengths
    })
    df_out.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Output written to: {OUTPUT_FILE}")

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()