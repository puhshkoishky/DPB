#API interface

from abc import ABC, abstractmethod

class APIInterface(ABC):
    @abstractmethod
    def fetch_data(self):
        """Method to fetch data from the API"""
        pass

    @abstractmethod
    def send_data(self, data):
        """Method to send data to the API"""
        pass
