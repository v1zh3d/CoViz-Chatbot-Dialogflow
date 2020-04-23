from flask import Flask, request, make_response
import requests
from requests.exceptions import HTTPError
import re
import pymongo
from pymongo import MongoClient
import json
import os
from flask_cors import cross_origin
from SendEmail.sendEmail import EmailSender
from config_reader import ConfigReader

app = Flask(__name__)


# geting and sending response to dialogflow
@app.route('/webhook', methods=['POST'])
@cross_origin()
def webhook():
    config_reader = ConfigReader()
    configuration = config_reader.read_config()

    client = MongoClient(
        "mongodb+srv://your_username:" + configuration["MONGO_PASSWORD"] + "@cluster0-p5lkb.mongodb.net/dialogflow?retryWrites=true&w=majority")

    db = client.dialogflow

    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    intent_check = req.get("queryResult").get("intent").get("displayName")

    if (intent_check == "AboutCorona" or
        intent_check == "CountryCases" or
        intent_check == "CovidMap" or
        intent_check == "CovidTest" or
        intent_check == "Fallback" or
        intent_check == "Goodbye" or
        intent_check == "Menu" or
        intent_check == "MyAreaCases" or
        intent_check == "MythBuster" or
        intent_check == "Precaution" or
        intent_check == "QuarantineTips" or
        intent_check == "StateCases" or
        intent_check == "Symptoms" or
        intent_check == "Welcome"):
        res = saveToDb(req, db)
    elif intent_check == "GetCountryName":
        res = getCountryName(req, db)
    elif intent_check == "GetStateName":
        res = getStateName(req, db)
    elif intent_check == "GetUserDetails":
        res = getUserDetails(req, db)
    elif intent_check == "GlobalCases":
        res = globalCases(req, db)
    elif intent_check == "IndiaCases":
        res = indiaCases(req, db)
    elif intent_check == "News":
        res = news(req, db)

    res = json.dumps(res, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def saveToDb(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    bot_says = result.get("fulfillmentText")
    if db.conversations.find({"sessionID": sessionID}).count() > 0:
        db.conversations.update_one({"sessionID": sessionID}, {
                                "$push": {"events": {"$each": [user_says, bot_says]}}})
    else:
        db.conversations.insert_one(
            {"sessionID": sessionID, "events": [user_says, bot_says]})
    print("Conversation Saved to Database!")


def getCountryName(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    country = result.get("parameters").get("country")
    country = country.lower()
    country = country.capitalize()
    if country == "USA" or country == "usa" or country == "United States Of America":
        country = "United States of America"
    elif country == "UK" or country == "uk":
        country = "United Kingdom"
    elif country == "UAE" or country ==  "uae":
        country = "United Arab Emirates"
    try:
        url = "https://api.covid19api.com/summary"
        res = requests.get(url)
        jsonRes = res.json()
        countryWiseCases = jsonRes["Countries"]
        print(len(countryWiseCases))
        for i in range(len(countryWiseCases)):
            if countryWiseCases[i]["Country"] == country:
                confirmed = str(countryWiseCases[i]["TotalConfirmed"])
                recovered = str(countryWiseCases[i]["TotalRecovered"])
                deaths = str(countryWiseCases[i]["TotalDeaths"])
                fulfillmentText = country + " stats of COVID-19 are: \nConfirmed Cases: " + confirmed + "\nRecovered Cases: " + recovered + "\nDeaths: " + deaths
                bot_says = fulfillmentText
                if db.conversations.find({"sessionID": sessionID}).count() > 0:
                    db.conversations.update_one({"sessionID": sessionID}, {"$push": {"events": {"$each": [user_says, bot_says]}}})
                else:
                    db.conversations.insert_one({"sessionID": sessionID, "events": [user_says, bot_says]})
                return {
                    "fulfillmentText": fulfillmentText
                }
        else:
            fulfillmentText = "Sorry we could not find any country named " + country + ". It might be a misspelling or we don't have record of the country."
            bot_says = fulfillmentText
            if db.conversations.find({"sessionID": sessionID}).count() > 0:
                db.conversations.update_one({"sessionID": sessionID}, {
                                        "$push": {"events": {"$each": [user_says, bot_says]}}})
            else:
                db.conversations.insert_one(
                    {"sessionID": sessionID, "events": [user_says, bot_says]})
            return {
                "fulfillmentText": fulfillmentText
            }

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


def getStateName(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    state = result.get("parameters").get("state")
    state = state.lower()
    state = state.capitalize()
    try:
        url = "https://api.covid19india.org/data.json"
        res = requests.get(url)
        jsonRes = res.json()
        stateWiseCases = jsonRes["statewise"]
        for i in range(len(stateWiseCases)):
            if stateWiseCases[i]["state"] == state:
                confirmed = str(stateWiseCases[i]["confirmed"])
                active = str(stateWiseCases[i]["active"])
                recovered = str(stateWiseCases[i]["recovered"])
                deaths = str(stateWiseCases[i]["deaths"])
                fulfillmentText = state + " stats of COVID-19 are: \nConfirmed Cases: " + confirmed + "\nActive Cases: " + active + "\nRecovered Cases: " + recovered + "\nDeaths: " + deaths
                bot_says = fulfillmentText
                if db.conversations.find({"sessionID": sessionID}).count() > 0:
                    db.conversations.update_one({"sessionID": sessionID}, {
                                            "$push": {"events": {"$each": [user_says, bot_says]}}})
                else:
                    db.conversations.insert_one(
                        {"sessionID": sessionID, "events": [user_says, bot_says]})
                return {
                    "fulfillmentText": fulfillmentText
                }
        else:
            fulfillmentText = "Sorry we could not find any state named " + state + ". It might be a misspelling or we don't have record of the state."
            bot_says = fulfillmentText
            if db.conversations.find({"sessionID": sessionID}).count() > 0:
                db.conversations.update_one({"sessionID": sessionID}, {
                                        "$push": {"events": {"$each": [user_says, bot_says]}}})
            else:
                db.conversations.insert_one(
                    {"sessionID": sessionID, "events": [user_says, bot_says]})
            return {
                "fulfillmentText": fulfillmentText
            }

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


def getUserDetails(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    name = result.get("parameters").get("name")
    email = result.get("parameters").get("email")
    mobile = result.get("parameters").get("mobile")
    pincode = result.get("parameters").get("pincode")
    regex_email = "^\w+@[a-zA-Z_]+?\.[a-zA-Z]{2,3}$"
    regex_mobile = "[0-9]{10}"
    regex_pincode = "[0-9]{6}"
    if re.search(regex_email, email) is None:
        fulfillmentText = "Not a valid email. Please start again and enter valid email."
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                                    "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }
    if re.search(regex_mobile, mobile) is None:
        fulfillmentText = "Not a valid mobile number. Please start again and enter valid mobile number."
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                                    "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }
    if re.search(regex_pincode, pincode) is None:
        fulfillmentText = "Not a valid pincode. Please start again and enter valid pincode."
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                                    "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }
    try:
        url = "https://api.postalpincode.in/pincode/" + pincode
        res = requests.get(url)
        jsonRes = res.json()
        postOffice = jsonRes[0]["PostOffice"]
        state = str(postOffice[0]["State"])
        if "&" in state:
            state = state.replace("&", "and")
        district = str(postOffice[0]["District"])
        if "&" in district:
            district = district.replace("&", "and")
        if district == "Ahmedabad":
            district = "Ahmadabad"
        elif district == "Bangalore":
            district = "Bengaluru"
        elif district == "Central Delhi":
            district = "New Delhi"
        print(state, end=',')
        print(district)
        try:
            url1 = "https://api.covid19india.org/v2/state_district_wise.json"
            res1 = requests.get(url1)
            jsonRes1 = res1.json()
            stateDistrictData = jsonRes1
            for i in range(len(stateDistrictData)):
                stateDistrictData1 = stateDistrictData[i]
                if stateDistrictData1["state"] == state:
                    districtData = stateDistrictData1["districtData"]
                    for j in range(len(districtData)):
                        email_sender = EmailSender()
                        if districtData[j]["district"] == district:
                            confirmed = str(districtData[j]["confirmed"])
                            print(f"\n Confirmed Cases are: {confirmed}")
                            email_file = open(
                                "email-templates/email-template-district.html", "r")
                            email_message = email_file.read()
                            email_sender.sendEmailDistrict(
                                name, email, district, confirmed, email_message)
                            fulfillmentText = "A mail has been sent to you with current COVID-19 cases in your area."
                            bot_says = fulfillmentText
                            if db.conversations.find({"sessionID": sessionID}).count() > 0:
                                db.conversations.update_one({"sessionID": sessionID}, {
                                    "$push": {"events": {"$each": [user_says, bot_says]}}})
                            else:
                                db.conversations.insert_one(
                                    {"sessionID": sessionID, "events": [user_says, bot_says]})
                            return {
                                "fulfillmentText": fulfillmentText
                            }
                    else:
                        fulfillmentText = "Sorry we did not found any data of COVID-19 in " + district + ". It might be a misspelling or we don't have record of the district."
                        bot_says = fulfillmentText
                        if db.conversations.find({"sessionID": sessionID}).count() > 0:
                            db.conversations.update_one({"sessionID": sessionID}, {
                                "$push": {"events": {"$each": [user_says, bot_says]}}})
                        else:
                            db.conversations.insert_one(
                                {"sessionID": sessionID, "events": [user_says, bot_says]})
                        return {
                            "fulfillmentText": fulfillmentText
                        }

        except HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


def globalCases(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    try:
        url = "https://api.covid19api.com/summary"
        res = requests.get(url)
        jsonRes = res.json()
        totalGlobalCases = jsonRes["Global"]
        confirmed = str(totalGlobalCases["TotalConfirmed"])
        recovered = str(totalGlobalCases["TotalRecovered"])
        deaths = str(totalGlobalCases["TotalDeaths"])
        fulfillmentText = "Confirmed Cases: " + confirmed + "\nRecovered Cases: " + recovered + "\nDeaths: " + deaths
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")



def indiaCases(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    try:
        url = "https://api.covid19india.org/data.json"
        res = requests.get(url)
        jsonRes = res.json()
        totalIndiaCases = jsonRes["statewise"][0]
        confirmed = str(totalIndiaCases["confirmed"])
        active = str(totalIndiaCases["active"])
        recovered = str(totalIndiaCases["recovered"])
        deaths = str(totalIndiaCases["deaths"])
        fulfillmentText = "Confirmed Cases: " + confirmed + "\nActive Cases: " + active + "\nRecovered Cases: " + recovered + "\nDeaths: " + deaths
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


def news(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    try:
        config_reader = ConfigReader()
        configuration = config_reader.read_config()
        url = "http://newsapi.org/v2/top-headlines?country=in&category=health&apiKey=" + \
            configuration['NEWS_API']
        res = requests.get(url)
        jsonRes = res.json()
        articles = jsonRes["articles"]
        news = list()
        for i in range(len(articles)):
            title = articles[i]["title"]
            author = articles[i]["author"]
            news_final = str(i + 1) + ". " + \
                str(title) + " - " + str(author)
            news.append(news_final)
        fulfillmentText = "\n".join(news)
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("Starting app on port %d" % port)
    app.run(debug=False, port=port, host="0.0.0.0")
