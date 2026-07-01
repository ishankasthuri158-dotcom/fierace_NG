from dns_engine import lookup_records
import json

if __name__ == "__main__":
    result = lookup_records("example.com")
    print(json.dumps(result, indent=2))
