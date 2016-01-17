# Created using Python 2.7.10
from urllib2 import Request, urlopen, URLError, HTTPError
from json import loads, dumps
import ssl
import datetime
import time
import re
import csv
import sys

# the base_url will be the url to your service machine
base_url = 'https://server:14101'
suppress_ssl_check = True


def call_api(url, request_data):
    """ Sends our request to the service and returns the data asked for"""
    req_object = Request(base_url + url, dumps(request_data))
    # We need to set the header of each our request to make sure it sends json
    req_object.add_header('Content-Type', 'application/json')
    try:
        # 10 second time out may need to be adjusted for your environment
        if suppress_ssl_check:
            response = urlopen(req_object, timeout=10, context=ssl._create_unverified_context())
        else:
            response = urlopen(req_object, timeout=10)
        result = loads(response.read())
    except URLError, e:
        try:
            # On error, most if not all of AFENav API calls will return a json object.
            # If an error is thrown trying to read the response json object then the service has thrown an exception
            # and we should end the process before going any further.
            error = loads(e.read())
            error_message = error['Message']
        except ValueError, e:
            print "Response object read error: " + e.message
            raise
        print 'Something bad happened: ' + error_message
        raise  # pass the exception on to the caller
    return result


def main():
    """
    This is an example of how to use the API to query documents in AFENav.
    We are retrieving a list of all AFE's that have a description which contains a search term.
    The results are then spit out to the console in a CSV format.
    Then we open each AFE and modify the description and save the document.
    """
    auth_token = ''

    try:
        # you will need to change the username and password to suit your environment
        # this may fail if no licenses are available
        result = call_api('/api/Authentication/Login', {
          'UserName': 'System Admin',
          'Password': '1'
        })

        # once logged in, we get an authentication token back from the service.
        # auth tokens are needed for almost all API requests
        auth_token = result['AuthenticationToken']

        print("Logged in.  AuthenticationToken = " + auth_token)

        result = call_api('/api/Afe/FieldCosts/Import', {
          "AuthenticationToken": auth_token,
          "AFEs": [
            { # <Afe>
              'AFE': '07J166',
              'Comment': 'Imported %s' % (time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())),
              #'YearEndIncurred': 100,
              #'UpdatedProjectEstimate': 1000,
              'Costs': [
                { # <Cost>
                  'CostYear': 2015,
                  'CostMonth': 12,
                  'Mode': 'INCREMENTAL',
                  'Amounts': [
                    {
                      'Account': '9210.219',
                      'GrossAmount': 200
                    }
                  ]
                }, # </Cost>
                { # <Cost>
                  'CostYear': 2016,
                  'CostMonth': 1,
                  'Mode': 'TOTAL',
                  'Amounts': [
                    {
                      'Account': '9210.219',
                      'GrossAmount': 500
                    },
                    {
                      'Account': '9210.237',
                      'GrossAmount': 300
                    }
                  ]
                } # </Cost>
              ]
            } # </Afe>
          ]
          })

        if result['Success']:
          print("Import had no errors.")
        else:
          print("Import had errors.")

        for message in result['Messages']:
          print("%s\t\t - %s" % (message["MessageType"], message["Message"]))


    finally:
        # As a best practise we should always log out once we are done. This finally block does this for us even when
        # an error is encountered.
        if auth_token != '':
            call_api('/api/Authentication/Logout', {'AuthenticationToken': auth_token})
            print("Logged out and released license")


# Run the main program
if __name__ == '__main__':
    main()
