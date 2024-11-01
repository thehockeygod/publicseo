# Run google cloud function locally
#Assumptions: 
#      You downloaded your google cloud run file called Main.py
#      Here my main function in the cloud main.py file is called run_serprecon - you should change this to your real value everywhere it exxists in the code below
#      Also, make sure your JSON is updated to be whatever you're actually passing to your functions


from dataclasses import dataclass
from typing import Any
from main import run_serprecon

@dataclass
class MockRequest:
    _json: dict

    def get_json(self, silent=True):
        return self._json

def run_locally() -> Any:
    # Exact JSON structure that would normally be sent via HTTP
    test_data = {
        "apikey": "your_value",
        "keyword": "whatever",
        "urls": [
            "https://www.ryanmjones.com",
            "https://www.serprecon.com"
        ]
    }
    
    # Create mock request
    mock_request = MockRequest(_json=test_data)
    
    # Call the cloud function directly
    result = run_serprecon(mock_request)
    return result

if __name__ == "__main__":
    result = run_locally()
    print(result)
