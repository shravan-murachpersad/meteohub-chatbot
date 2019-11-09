# coding=utf-8

from __future__ import print_function
from flask import make_response
from flask import request
from flask import Flask
import os
import json
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from urllib.parse import urlparse, urlencode
from future.standard_library import install_aliases
from apscheduler.schedulers.blocking import BlockingScheduler

install_aliases()

# Flask app should start in global layout
app = Flask(__name__)
agent = ""
platform = ""

@app.route('/webhook', methods=['POST'])
def webhook():
    botRequest = request.get_json(silent=True, force=True)

    agent = botRequest.get("session").split("/")[1]
    platform = botRequest.get("originalDetectIntentRequest").get("source").upper()
    
    res = processRequest(botRequest)
    res = json.dumps(res, indent=4)

    response = make_response(res)
    response.headers['Content-Type'] = 'application/json'

    return response

@app.route('/ping', methods=['GET'])
def ping():
    return '', 200

def processRequest(req):
    if req.get("queryResult").get("action") == "subscribe":
        return newSubscription(req)

    if req.get("queryResult").get("action") == "weather":
        result = req.get("result")
        parameters = result.get("parameters")

        location = parameters.get("location")
        datetime = parameters.get("date-time")

        if location is None:
            return None

        params = {"location": location}

        if datetime is not None:
            params["datetime"] = datetime

        httpRequest = "http://meteohub.projexel.info/api/weatherforecast?" + \
            urlencode(params)

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

def newSubscription(req):
    subscriberId = req.get("originalDetectIntentRequest").get("payload").get("data").get("sender").get("id")

    httpRequest = "http://localhost:8080/meteohub.svc/checkSubscription?subscriberId=" + subscriberId

    try:
        result = urlopen(httpRequest).read()

        cardData = {
            'title': "You are already subscribe with MCM.",
            'subtitle': "You can unsubscribe anytime by sending UNSUBSCRIBE.",
            'image_url': "https://blog.vantagecircle.com/content/images/size/w730/2019/09/welcome.png"
        }

        return GenerateCard(cardData);
    except HTTPError as e:
        if e.code == 404:
            subscriberData = {
                "subscriberId": subscriberId,
                "platform": platform,
                "status": "ACTIVE",
                "agent": agent
            }

            subscriberData = json.dumps(subscriberData)
            subscriberData = str(subscriberData)
            subscriberData = subscriberData.encode('utf-8')

            httpRequest = "http://localhost:8080/meteohub.svc/subscribe"

            try:
                headers = {'Content-type': 'application/json'}

                newSubscriptionReq = Request(httpRequest, data=subscriberData, headers=headers)
                newSubscriptionRes = urlopen(newSubscriptionReq)

                cardData = {
                    'title': "Thanks for subscribing with MCM.",
                    'subtitle': "You will be the first to receive weather alerts on your mobile. Stay tuned.",
                    'image_url': "https://blog.vantagecircle.com/content/images/size/w730/2019/09/welcome.png"
                }

                return GenerateCard(cardData);
            except Exception as f:
                cardData = {
                    'title': "Failed to subscribe.",
                    'subtitle': "An error has occured. Please try again.",
                    'image_url': "http://www.samsungsfour.com/images/exclamation.png"
                }

                return GenerateCard(cardData);

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
