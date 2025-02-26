#api2 implemnentation


from api_interface import APIInterface

class API2(APIInterface):
    def fetch_data(self):
        # Replace with actual API logic for API2
        print("Fetching data from API2...")
        return {"data": "API2 data"}

    def send_data(self, data):
        # Replace with actual API logic for sending data to API2
        print(f"Sending data to API2: {data}")
        return {"status": "success"}
