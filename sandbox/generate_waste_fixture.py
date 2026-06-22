import json
from agents.ingestion import run as ingest
from agents.classification import run as classify

# 1. Read raw transactions
with open("data/sample_transactions.json") as f:
    raw_data = json.load(f)

# 2. Ingestion
ingestion_result = ingest(raw_data)
transactions = ingestion_result["transactions"]

# 3. Classification
classification_result = classify({"transactions": transactions})
vendor_matches = classification_result["vendor_matches"]

# 4. Combined state
state = {
    "transactions": transactions,
    "vendor_matches": vendor_matches
}

# 5. Write
with open("data/sample_waste_input.json", "w") as f:
    json.dump(state, f, indent=2, default=str)

print("Fixture written to data/sample_waste_input.json")