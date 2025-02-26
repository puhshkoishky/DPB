#api1 implementationfrom api_interface import APIInterface

class API1(APIInterface):
    def fetch_data(self):
        # Replace with actual API logic for API1
        print("Fetching data from API1...")
        return {"data": "API1 data"}

    def send_data(self, data):
        # Replace with actual API logic for sending data to API1
        print(f"Sending data to API1: {data}")
        return {"status": "success"}

