import requests
import concurrent.futures

# URL of the website to stress test
URL = "https://puppylove.pclub.in/"

# Number of requests to send
NUM_REQUESTS = 1000000

# Number of concurrent threads to use
CONCURRENT_THREADS = 10000

# Function to send a single request
def send_request(session):
    try:
        response = session.get(URL)
        # Print status code and response time
        print(f"Status Code: {response.status_code}, Response Time: {response.elapsed.total_seconds():.2f}")
    except Exception as e:
        print(f"Request failed: {e}")

# Main function to perform stress testing
def stress_test():
    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
            # Submit all the requests
            futures = [executor.submit(send_request, session) for _ in range(NUM_REQUESTS)]
            
            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(futures):
                future.result()

if __name__ == "__main__":
    print("Starting stress test...")
    while(button_pressed):
        stress_test()
    print("Stress test completed.")