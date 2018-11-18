# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 2018

@author: Thao
"""

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import json
from flask import Flask, request, make_response, jsonify
import datetime
from datetime import date

# Fetch the service account key JSON file contents
cred = credentials.Certificate('/Users/thaonguyen/Documents/Studium/Data Science/Teamprojekt/Seminar-b253e5498290.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://seminar-b9c58.firebaseio.com/'
})


# initialize the flask app
app = Flask(__name__)

# create a route for webhook
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():

    # build a request object
    req = request.get_json(silent=True, force=True)
    
    # fetch action from json
    try:
        action = req.get('queryResult').get('action')
    except AttributeError:
        return 'json error'
    
    if action == 'showBookings':
        res = show_bookings(req)
    elif action == 'bookSeminar':
        res = book_seminar(req)
    elif action == 'seminarInfo':
        res = seminar_info(req)
    else:
        log.error('Unexpected action.')

    print('Action: ' + action)
    print('Response: ' + res)

    # return response
    return make_response(jsonify({'fulfillmentText':res}))

# function for responses
def show_bookings(req):
    # Initialize result as empty    
    res = "You are not in our database. Please contact HR."
    
    firstname = req.get('queryResult').get('parameters').get('firstname')
    lastname = req.get('queryResult').get('parameters').get('lastname')
    bookingtype = req.get('queryResult').get('parameters').get('bookingtype')
    
    employeesRef = db.reference('employees')
    employees = employeesRef.get()
    
    #matching employer's name with their ID
    for i in range(len(employees)):
        if employees[i]["First_name"] == firstname:
            if employees[i]["Last_name"] == lastname:
                matchingID = employees[i]["employee_id"]
                break
    
    if 'matchingID' in locals():
        bookingRef = db.reference('bookings')
        bookings = bookingRef.get()
        bookedSeminars = []

        #collecting booked seminars
        i=0
        if bookingtype == 'past':
            while i < len(bookings):
                if bookings[i]["employee_id"] == matchingID and datetime.datetime.strptime(bookings[i]["date"], '%d/%m/%y').date() < date.today():
                    sem = bookings[i]["seminar_title"] + " on " + str(bookings[i]["date"]) + " in " + bookings[i]["location"]
                    bookedSeminars.append(sem)
                i+=1
            bookedSeminars = ', '.join(bookedSeminars)       
        elif bookingtype == 'upcoming':
            while i < len(bookings):
                if bookings[i]["employee_id"] == matchingID and datetime.datetime.strptime(bookings[i]["date"], '%d/%m/%y').date() >= date.today():
                    sem = bookings[i]["seminar_title"] + " on " + str(bookings[i]["date"]) + " in " + bookings[i]["location"]
                    bookedSeminars.append(sem)
                i+=1
            bookedSeminars = ', '.join(bookedSeminars) 
        else:
            while i < len(bookings):
                if bookings[i]["employee_id"] == matchingID:
                    sem = bookings[i]["seminar_title"] + " on " + str(bookings[i]["date"]) + " in " + bookings[i]["location"]
                    bookedSeminars.append(sem)
                i+=1
            bookedSeminars = ', '.join(bookedSeminars) 

        if not bookedSeminars:
            res = "There are no seminars according your request."
        else: 
            res = "These are your booked seminars: " + bookedSeminars

 # TO BE DONE: chronological sorting, next seminar (week, month)
 # return a fulfillment response
    return res

def book_seminar(req):
    res = "You are not in our database. Please contact HR."
    
    firstname = req.get('queryResult').get('parameters').get('firstname')
    lastname = req.get('queryResult').get('parameters').get('lastname')
    course = req.get('queryResult').get('parameters').get('course')
    city = req.get('queryResult').get('parameters').get('city')
    
    employeesRef = db.reference('employees')
    employees = employeesRef.get()
    seminarRef = db.reference('seminars')
    seminars = seminarRef.get()
    bookingRef = db.reference('bookings')
    bookings = bookingRef.get()
    countRef = db.reference('counts')
    counts = countRef.get()

    #matching employer's name with their ID
    for i in range(len(employees)):
        if employees[i]["First_name"] == firstname:
            if employees[i]["Last_name"] == lastname:
                employee_id = employees[i]["employee_id"]
                break

    #check availability
    if "employee_id" in locals():
        res = "The seminar you requested is not being offered in " + city + "."

        for j in range(len(seminars)):
            breaker = False
            for k in range(len(seminars[j]["description"])):
                if seminars[j]["description"][k].lower() == course.lower():
                    seminar_id = seminars[j]["seminar_id"]
                    breaker = True
                    break
            if breaker== True:
                break
        
        if "seminar_id" in locals():
            seminar = seminars[seminar_id]

            #check location
            for l in range(len(seminar["locations"])):
                breaker = False
                if seminar["locations"][l]==city:
                    res = "All seminars about " + course + " are booked out. You will be informed if new dates are available."
                    
                    #check occupancy
                    if seminar["capacity"] > seminar["occupancy"]:
                        occupancy = seminar["occupancy"]
                        res = "Unfortunately, you missed our last seminar about " + course + ". You will be informed if new dated are available."
                    
                        #check if already booked
                        i = 0
                        while i < len(bookings):
                            if bookings[i]["employee_id"] == employee_id and bookings[i]["location"] == city and bookings[i]["seminar_id"] == seminar_id:
                                res = "You have already booked the seminar " + course + " in "+city+" on " + bookings[i]["date"]+"."
                                breaker = True
                                break
                            i+=1

                        if breaker:
                            break
                        else:
                            #check next date
                            for m in range(len(seminar["dates"])):
                                if datetime.datetime.strptime(seminar["dates"][m], '%d/%m/%y').date() > date.today():
                                    seminar_date = str(seminar["dates"][m])

                                    #Update occupancy
                                    seminarRef.child(str(seminar_id)).update({"occupancy": occupancy + 1})

                                    #Update bookingcount
                                    booking_count = counts['booking_count'] + 1
                                    countRef.update({"booking_count": booking_count})

                                    #Write to DB
                                    bookingRef.update({
                                        str(booking_count): {
                                            'date': seminar_date,
                                            'employee_id': employee_id,
                                            'location': city,
                                            'seminar_id': seminar_id,
                                            'seminar_title': seminar["title"]
                                        }})
                                    res = "Your booking request for the seminar " + course + " in "+city+" on " + seminar_date + " has been forwarded. You will receive a confirmation via email."
                                    breaker = True
                                    break
                        if breaker:
                            break

#TO BE DONE: date suggestion, location alternative, capacity check
    return res

def seminar_info(req):
    course = req.get('queryResult').get('parameters').get('course')
    userlevel = req.get('queryResult').get('parameters').get('userlevel')

    seminarRef = db.reference('seminars')
    seminars = seminarRef.get()

    for j in range(len(seminars)):
        breaker = False
        for k in range(len(seminars[j]["description"])):
            if seminars[j]["description"][k].lower() == course.lower():
                seminar_id = seminars[j]["seminar_id"]
                breaker = True
                break
        if breaker == True:
            break

    if "seminar_id" in locals():
        seminar = seminars[seminar_id]
        res = "We are offering the seminar " + seminar["title"] + " which is described as followed: \n"
        res = res + seminar["text"]
    else:
        res = "We don't have seminars that matches your request."

    return res

# run the app
if __name__ == '__main__':
   app.run()
