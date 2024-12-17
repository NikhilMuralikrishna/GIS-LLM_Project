
![GeoGPT Logo](LOGO.png)

# GeoGPT Project

## Setup Instructions

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/NikhilMuralikrishna/GeoGPT_Project.git
   cd GeoGPT_Project

2. **Create a Virtual Environment**
   ```bash
   python -m venv env
   source env/bin/activate   # On Linux/Mac
   env\Scripts\activate      # On Windows

3. **Install Dependencies**
   Use pip to install the required dependencies:
   ```bash
   pip install -r requirements.txt


4. **Set Up Environment Variables**

   Create a .env file in the root directory and add your OpenAI API key in congif.ini:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   ```
   Replace your_api_key_here with your actual API key

5. **Run the Application**
   Start the program with:
   ```bash
   GeoGPT.py
