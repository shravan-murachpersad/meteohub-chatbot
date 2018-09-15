# coding=utf-8

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    # print(json.dumps(req, indent=4))

    res = processRequest(req)
    res = json.dumps(res, indent=4)

    response = make_response(res)
    response.headers['Content-Type'] = 'application/json'
    return response


def processRequest(req):
    if req.get("result").get("action") == "weather":
        result = req.get("result")
        parameters = result.get("parameters")

        location = parameters.get("location")
        datetime = parameters.get("date-time")

        if location is None:
            return None

        params = { "location":location }

        if datetime is not None:
            params["datetime"] = datetime

        httpRequest = "http://meteohub.projexel.info/api/weatherforecast?" + urlencode(params)

        result = urlopen(httpRequest).read()

        data = weatherResponse(json.loads(result))

        return data


def weatherResponse(data):
    location = data.get("location")
    forecast = data.get("forecast")
    current_conditions = data.get('current_conditions')

    if forecast is not None:
        conditions = forecast.get("conditions")
        minTemp = forecast.get("low").get("celsius")
        maxTemp = forecast.get("high").get("celsius")
        icon_url = forecast.get("icon_url")
        wind = str(forecast.get("avewind").get("kph"))
        wind_dir = forecast.get("avewind").get("dir")

        data = {
            'title': conditions,
            'subtitle': "min " + minTemp + " °C / " + maxTemp + " max. Wind: " + wind_dir + " at about " + wind + " km/h",
            'image_url': icon_url
        }

        return {
            "data": GenerateCard(data),
            "source": "meteohub"
        }

    if current_conditions is not None:
        conditions = current_conditions.get("weather")
        minTemp = str(current_conditions.get("temp_c"))
        maxTemp = str(current_conditions.get("feelslike_c"))
        icon_url = current_conditions.get("icon_url")
        wind = str(current_conditions.get("wind_kph"))
        wind_dir = current_conditions.get("wind_dir")

        data = {
            'title': conditions,
            'subtitle': "min " + minTemp + " °C / " + maxTemp + " max. Wind " + wind_dir + " at about " + wind + " km/h",
            'image_url': icon_url,
        }

        return {
            "data": GenerateCard(data),
            "source": "meteohub"
        }




def GenerateCard(data):
    title = data.get("title")
    subtitle = data.get("subtitle")
    image_url = data.get("image_url")
    default_action = data.get("default_action")
    buttons = data.get("buttons")

    return {
        'facebook': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': [
                        {
                            'title': title,
                            'image_url': image_url,
                            'subtitle': subtitle,
                            'default_action': default_action,
                            'buttons': buttons
                        }
                    ]
                }
            }
        }
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
