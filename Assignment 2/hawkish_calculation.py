import os
import re
import json
import pandas as pd
import torch
from nltk.tokenize import sent_tokenize
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm
from huggingface_hub import login

# ========== Setup ==========

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("gtfintechlab/FOMC-RoBERTa")
model = AutoModelForSequenceClassification.from_pretrained("gtfintechlab/FOMC-RoBERTa")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

# Tariff-related keywords
tariff_keywords = [
    'tariff', 'tariffs', 'import duty', 'import duties', 'customs duty', 'customs duties', 'export tariffs',
    'retaliation', 'retaliatory tariffs', 'trade war', 'trade wars', 'trade dispute', 'trade barriers',
    'trade agreement', 'trade negotiations', 'trade tensions', 'section 301', 'section 232',
    'china tariffs', 'us-china trade', 'global trade tensions', 'supply chain disruption'
]

# ========== Functions ==========

def predict_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=1).detach().cpu().numpy()[0]
    return {'positive': probs[1], 'neutral': probs[0], 'negative': probs[2]}

def is_tariff_related(text):
    text = re.sub(r'[^a-z\s]', ' ', text.lower())
    return any(k in text for k in tariff_keywords)

def analyze_document(doc):
    content = doc.get("content")
    if not content:
        try:
            with open(doc['filepath'], 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            content = ""

    segments = sent_tokenize(content)
    results = []

    for seg in segments:
        sentiment = predict_sentiment(seg)
        tariff_flag = is_tariff_related(seg)
        results.append({
            "segment": seg,
            **sentiment,
            "is_tariff": tariff_flag
        })

    df = pd.DataFrame(results)
    total = len(df)
    if total == 0:
        return None

    hawkish = (df['positive'] > df['negative']).sum()
    dovish = (df['negative'] > df['positive']).sum()
    tariff_df = df[df['is_tariff']]

    return {
        "Date": doc.get("date"),
        "Filename": doc.get("filename"),
        "Title": doc.get("title"),
        "Speaker": doc.get("speaker"),
        "Source Type": doc.get("source_type"),
        "Total Segments": total,
        "Hawkish %": hawkish / total * 100,
        "Dovish %": dovish / total * 100,
        "Neutral %": df['neutral'].mean() * 100,
        "Polarity Score": (df['positive'] - df['negative']).mean(),
        "Tariff Mentions": len(tariff_df),
        "Tariff % of Doc": len(tariff_df) / total * 100 if total > 0 else 0,
        "Tariff Polarity Score": (tariff_df['positive'] - tariff_df['negative']).mean() if not tariff_df.empty else 0
    }

def process_json_file(json_path, output_csv_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for doc in tqdm(data, desc=f"Processing {os.path.basename(json_path)}"):
        result = analyze_document(doc)
        if result:
            results.append(result)

    df = pd.DataFrame(results)
    df.to_csv(output_csv_path, index=False)
    print(f"[✓] Saved: {output_csv_path}")

# ========== Main ==========

if __name__ == "__main__":
    os.makedirs("sentiment_results", exist_ok=True)

    sources = {
        "./data/standardized/unified_minutes.json": "./sentiment_results/fomc_minutes_analysis.csv",
        "./data/standardized/unified_press_conferences.json": "./sentiment_results/press_conferences_analysis.csv",
        "./data/standardized/unified_speeches.json": "./sentiment_results/fed_speeches_analysis.csv"
    }

    for input_path, output_path in sources.items():
        process_json_file(input_path, output_path)
