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
import dateparser
import pytz

# Fetch the service account key JSON file contents
cred = credentials.Certificate('C:\\Users\\Tobias\\Documents\\Uni Mannheim\\Team Project NLU\\service_account_key_thao.json')

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

    if action == 'get_names':
        res = show_bookings(req)
    elif action == 'bookSeminar':
        res = book_seminar(req)
    elif action == 'seminarInfo':
        res = seminar_info(req)
    elif action == 'cancelSeminar':
        res = cancel_seminar(req)
    else:
        log.error('Unexpected action.')
        print('error')

    print('Action: ' + action)
    print('Response: ' + res)

    # return response
    return make_response(jsonify({'fulfillmentText':res}))

# function for responses
def show_bookings(req):
    # Initialise result as empty    
    resp = "Your are not in our database. Please contact HR."
    
    # fetch parameters from json
    
    display_option = req.get('queryResult').get('parameters').get('display-option')
    seminar_date = req.get('queryResult').get('parameters').get('date')
    firstname = req.get('queryResult').get('parameters').get('firstname')
    lastname = req.get('queryResult').get('parameters').get('lastname')
    date_period = req.get('queryResult').get('parameters').get('date-period')
    bookingtype = req.get('queryResult').get('parameters').get('booking-type')
    city = req.get('queryResult').get('parameters').get('geo-city')
    
    employeesRef = db.reference('employees')
    employees = employeesRef.get()
   
    for i in range(len(employees)):
        if employees[i]["First_name"] == firstname:
            if employees[i]["Last_name"] == lastname:
                matchingID = employees[i]["employee_id"]
                break
                
    if 'matchingID' in locals():
        bookingRef = db.reference('bookings')
        bookings = bookingRef.get()
        bookedSeminars = set([])

        if bookingtype == 'past':
            for i in range(len(bookings)):
                if not "cancellation" in bookings[i]:
                    if dateparser.parse(bookings[i]["date"]).date() < date.today():
                        if  bookings[i]["employee_id"] == matchingID:
                            sem = bookings[i]["seminar_title"] + " on " + bookings[i]["date"] + " in " + bookings[i]["location"]
                            bookedSeminars.add(sem)
        elif bookingtype == 'upcoming':
            for i in range(len(bookings)):
                if not "cancellation" in bookings[i]:
                    if dateparser.parse(bookings[i]["date"]).date() >= date.today():
                        if  bookings[i]["employee_id"] == matchingID:
                            sem = bookings[i]["seminar_title"] + " on " + bookings[i]["date"] + " in " + bookings[i]["location"]
                            bookedSeminars.add(sem)
        else:
            for i in range(len(bookings)):
                if not "cancellation" in bookings[i]:
                    if  bookings[i]["employee_id"] == matchingID:
                        sem = bookings[i]["seminar_title"]
                        bookedSeminars.add(sem)
        
        if len(bookedSeminars) != 0:
            if display_option == "next" or display_option == "upcoming":
                resp = "This is your next seminar: " + showNextBooking(bookedSeminars)
            elif seminar_date:
                resp = showBookingsOnGivenDate(seminar_date,bookedSeminars,matchingID)
            elif date_period:
                dateStart = date_period["startDate"]
                dateEnd = date_period["endDate"]
                resp = showBookingsWithinPeriod(dateStart, dateEnd, bookedSeminars, matchingID)
            elif city:
                resp = showBoookingsAtLocation(city, bookedSeminars, matchingID)
            else:
                bookedSeminars = ', '.join(bookedSeminars)   
                resp = "These are your booked seminars: " + bookedSeminars
        else:
            resp = "There are no recorded bookings for you."

    return resp
 # TO BE DONE: chronological sorting, next seminar (week, month)
 # return a fulfillment response

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
            print(seminar_id)
            print(j)
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
                            if not "cancellation" in bookings[i]:
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

def cancel_seminar(req):
    firstname = req.get('queryResult').get('parameters').get('firstname')
    lastname = req.get('queryResult').get('parameters').get('lastname')
    course = req.get('queryResult').get('parameters').get('course')
    city = req.get('queryResult').get('parameters').get('city')
    seminar_date = req.get('queryResult').get('parameters').get('date')

    employeesRef = db.reference('employees')
    employees = employeesRef.get()
    seminarRef = db.reference('seminars')
    seminars = seminarRef.get()
    bookingRef = db.reference('bookings')
    bookings = bookingRef.get()
    countRef = db.reference('counts')
    counts = countRef.get()

    res = "You are not in the database. Please contact HR."
    #matching employer's name with their ID
    for i in range(len(employees)):
        if employees[i]["First_name"] == firstname:
            if employees[i]["Last_name"] == lastname:
                employee_id = employees[i]["employee_id"]-1
                break

    #matching seminar ID
    for j in range(len(seminars)):
        breaker = False
        for k in range(len(seminars[j]["description"])):
            if seminars[j]["description"][k].lower() == course.lower():
                seminar_id = seminars[j]["seminar_id"]-1
                res = "You don't have bookings according your request."
                breaker = True
                break
        if breaker:
            break
    
    breaker = False
    if 'employee_id' in locals() and 'seminar_id' in locals():
        #search for corresponding booking
        for j in range(len(bookings)):
            if not "cancellation" in bookings[i]:
                if bookings[j]["employee_id"] == employee_id and bookings[j]["seminar_id"]== seminar_id and datetime.datetime.strptime(bookings[j]["date"], '%d/%m/%y').date() > date.today():
                    breaker_1 = True
                    breaker_2 = True
    
                    #check date in case user defined date
                    if seminar_date != "":
                        breaker_1 = (dateparser.parse(seminar_date).date() == dateparser.parse(bookings[j]["date"]).date())
    
                    #check location in case user defined date
                    if city != "":
                        breaker_2 = (city == bookings[j]["location"])
    
                    breaker = breaker_1 and breaker_2
    
                if breaker:
                    #cancel booking by deleting entries
                    seminar_date = bookings[j]["date"]
                    cancellation = "cancelled on " + str(date.today())
                    bookingRef.update({
                                str(j): {
                    				'cancellation': cancellation
                                }})
                    res = "Your seminar booking for " + course + " on " + seminar_date + " in " + city + " has been cancelled. You will receive a cancellation confirmation."
                    break
    return res

def showNextBooking(bookedSeminars):      
    
    bookingRef = db.reference('bookings')
    bookings = bookingRef.get()
    
    # Initialise date of next booking with first date in the list and iterate through all dates
    for i in range(len(bookings)):
        if not "cancellation" in bookings[i]:
            if bookings[i]["seminar_title"] in bookedSeminars:           
                temp = bookings[i]["date"]
                dateNext = dateparser.parse(temp).date() 
                break
                 
    for i in range(1,len(bookings)):
        if not "cancellation" in bookings[i]:
            if bookings[i]["seminar_title"] in bookedSeminars:      
                temp = bookings[i]["date"] 
                if dateparser.parse(temp).date() <= dateNext:
                    dateNext = dateparser.parse(temp).date() 
                    num = i 

    return bookings[num]["seminar_title"]

def showBookingsOnGivenDate(seminar_date,bookedSeminars,matchingID):
        
    bookingRef = db.reference('bookings')
    bookings = bookingRef.get()    
    given_date = dateparser.parse(seminar_date).date() 
    
    matchedSeminars = set([])
                    
    for i in range(len(bookings)):
        if not "cancellation" in bookings[i]:
            if (bookings[i]["seminar_title"] in bookedSeminars and
            dateparser.parse(bookings[i]["date"]).date() == given_date and
            bookings[i]["employee_id"] == matchingID):
                
                sem = bookings[i]["seminar_title"]
                matchedSeminars.add(sem)
                
    if len(matchedSeminars) != 0:
        return "Your booked seminars on " + given_date.strftime("%d.%m.%y") + ": " + ', '.join(matchedSeminars)
    else:
        return "There are no recorded bookings for you on the specified date."    
    
def showBookingsWithinPeriod(dateStart,dateEnd,bookedSeminars, matchingID):
    bookingRef = db.reference('bookings')
    bookings = bookingRef.get()
    start = dateparser.parse(dateStart)
    end = dateparser.parse(dateEnd)
    
#   If bookings between start and end, add them to the list of matched seminars

    matchedSeminars = set([])                    
    for i in range(len(bookings)):
        if not "cancellation" in bookings[i]:
            if (bookings[i]["seminar_title"] in bookedSeminars and
            start <= pytz.utc.localize(dateparser.parse(bookings[i]["date"])) <= end and
            bookings[i]["employee_id"] == matchingID):
                
                sem = bookings[i]["seminar_title"]
                matchedSeminars.add(sem)
                
    if len(matchedSeminars) != 0:
        return "Your booked seminars between " + start.strftime("%d.%m.%y") + " and " + end.strftime("%d.%m.%Y") + ": " + ', '.join(matchedSeminars)
    else:
        return "There are no recorded bookings for you within the specified period."            
    
def showBoookingsAtLocation(city, bookedSeminars, matchingID):
    bookingRef = db.reference('bookings')
    bookings = bookingRef.get()

    matchedSeminars = set([])                    
    for i in range(len(bookings)):    
        if not "cancellation" in bookings[i]:
            if (bookings[i]["seminar_title"] in bookedSeminars and
            bookings[i]["location"] == city and
            bookings[i]["employee_id"] == matchingID):
                
                sem = bookings[i]["seminar_title"]
                matchedSeminars.add(sem)
                
    if len(matchedSeminars) != 0:
        return "Your booked seminars in " + city + ": " + ', '.join(matchedSeminars)
    else:
        return "There are no recorded bookings for you in " + city               

# run the app
if __name__ == '__main__':
   app.run()
