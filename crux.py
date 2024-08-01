import requests
import json

#you need to enable this API first: https://developers.google.com/codelabs/chrome-web-vitals-psi-crux#2
#API key is needed 
API_KEY = "YOUR_API_KEY_HERE"

def extract_p75_values(json_string):
  """Extracts p75 values from the given JSON string.
  Args:
    json_string: The JSON string containing the data.
  Returns:
    A dictionary containing the extracted p75 values.
  """
  data = json.loads(json_string)

  metrics = [
      "interaction_to_next_paint",
      "largest_contentful_paint",
      "first_input_delay",
      "cumulative_layout_shift",
      "experimental_time_to_first_byte",
      "first_contentful_paint"
  ]

  p75_values = {}

  for metric in metrics:
    try:
      p75_value = data["record"]["metrics"][metric]["percentiles"]["p75"]
      p75_values[metric] = p75_value
    except KeyError:
      print(f"Error: Metric '{metric}' or its p75 value not found in JSON.")

  return p75_values


def PageSpeedInsights(url):
    # Build the request URL with your API key
    request_url = f"https://chromeuxreport.googleapis.com/v1/records:queryRecord?key={API_KEY}"

    # Prepare the data to send in JSON format
    data = {"url": url_to_query}

    # Set the headers for content type
    headers = {"Content-Type": "application/json"}

    # Send the request and get the response
    response = requests.post(request_url, headers=headers, json=data)

    # Check for successful response
    if response.status_code == 200:
        #print(response.text)
        p75_results = extract_p75_values(response.text)
        print(p75_results)
        return p75_results
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return ""


# Replace with the URL you want to query
url_to_query = "https://www.razorfish.com"
PageSpeedInsights(url_to_query)

#or do multiple URLs:
urls = ["https://www.noslang.com","https://www.seodataviz.com","https://www.razorfish.com","https://www.google.com"]

for url in urls:
    print(url)
    PageSpeedInsights(url)