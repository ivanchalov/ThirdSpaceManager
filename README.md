# Third Space Gym Class Booker

This Python project automatically books classes for you at Third Space Gym. It utilizes Selenium for web automation and integrates with Notion's API for scheduling. The script can be run locally or deployed to AWS Lambda. 

## Features

- Selenium-based automation for booking gym classes
- Notion API integration for managing the class schedule
- Supports AWS Lambda deployment 

## Setup & Installation

### Selenium on AWS Lambda

Follow the instructions to set up Selenium on AWS Lambda using Python 3.7. 

- YouTube Video: [Running Selenium on AWS Lambda](https://www.youtube.com/watch?v=b49Y3NGJX68)
- Medium Article: [Running Selenium and Headless Chrome on AWS Lambda Layers Python 3.6](https://medium.com/hackernoon/running-selenium-and-headless-chrome-on-aws-lambda-layers-python-3-6-bd810503c6c3)

### Notion API Integration

Enable Notion API integration for a page. The page needs to have a YAML code block in the following example format:

```
day_of_week [monday-sunday]:
  - name: "Class Name"
    time: "07:00"
    location: "Canary Wharf"
  - name: "Another Class Name"
    time: "16:15"
    location: "Soho"
```

### Install Python Libraries

Install the required Python libraries specified in `requirements.txt`. The script uses specific versions of Python, Selenium, and Chromedriver, so it is essential to install these specific versions.

```bash
pip install -r requirements.txt
```

### Environment Variables

Set up the following environment variables:

- `THIRD_SPACE_LOGIN` - Your gym login email
- `THIRD_SPACE_PASSWORD` - Your gym password
- `NOTION_API_KEY` - Notion API integration token
- `NOTION_PAGE_ID` - Notion page ID where the schedule is located

## Running the Script

You can run the script either locally or on AWS Lambda.

### Run Locally

```bash
python lambda_function.py
```

### Deploy on AWS Lambda

Upload your package to AWS Lambda and set it to use Python 3.7. Setup layers with libraries and chromedriver + headless-chromium as per YouTube instructions above.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)
