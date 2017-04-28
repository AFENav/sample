# Created using Python 2.7.10
from urllib2 import Request, urlopen, URLError, HTTPError, ssl
from json import loads, dumps
import datetime
import re
import csv
import sys

# the base_url will be the url to your service machine
base_url = 'https://server:14101'
suppress_ssl_check = True
username = 'System Admin'
password = 'CHANGEME'
searchstring = '07W089'

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
          'UserName': username,
          'Password': password
        })

        # once logged in, we get an authentication token back from the service.
        # auth tokens are needed for almost all API requests
        auth_token = result['AuthenticationToken']

        print("Logged in.  AuthenticationToken = " + auth_token)

        try:

          # Search for an AFE by AFE Number (or another identifier)
          result = call_api('/api/Documents/SearchAndOpenReadonly', {
            'AuthenticationToken': auth_token,
            'DocumentType': 'AFE',
            'SearchString': searchstring
          })

          doc_handle = result["DocumentHandle"]

          print("Found and opened document read-only.  DocumentHandle = " + doc_handle)

          # read the document structure for the AFE

          result = call_api('/api/Documents/Read', {
            'AuthenticationToken': auth_token,
            'DocumentHandle': doc_handle,
            'SerializeDocumentTypes': ['AFE','PARTNER','USER','AFENUMBER']
          })

          fields = {}

          # pull top-level fields into a dictionary for convenience
          for field in result["BaseDocument"]["Record"]["Fields"]:
            fields[field["Id"]] = field

          # pull custom fields into a dictionary for convenience
          for field in fields["CUSTOM"]["Record"]["Fields"]:
            fields["CUSTOM/" + field["Id"]] = field

          # retrieve AFE Number, if any, from child AFE Number document
          afenumber = ''
          for childDocument in result["ChildDocuments"]:
            if childDocument["DocumentId"] == fields["AFENUMBER_DOC"]["Document"] and childDocument["DocumentType"] == "AFENUMBER":
              for field in childDocument["Record"]["Fields"]:
                if field["Id"] == 'AFENUMBER':
                  afenumber = field['Text']

          print(" =========== HEADER INFORMATION ====================================== ")
          print("AFE Number = " + afenumber)
          print("Document ID = " + fields["DOCUMENT_ID"]["Guid"] + " (identifies a version of an AFE)")
          print("Chain ID = " + fields["CHAIN_GUID"]["Guid"] + " (identifies a family of AFE; same between BASE, REVs and SUPs)")
          print("AFE Description = " + fields["DESCRIPTION"]["Text"])
          print("AFE Version = " + fields["VERSION_STRING"]["Text"])
          print("AFE Status = " + fields["STATUS"]["Text"])
          print("AFE Type = " + fields["CUSTOM/AFE_TYPE"]["DocumentDescriptor"])
          print("Total Approved Estimate = " + str(fields["APPROVED_GROSS_ESTIMATE"]["NumberDecimal"]))
          print("Total Estimate = " + str(fields["TOTAL_GROSS_ESTIMATE"]["NumberDecimal"]))

          print("")
          print(" =========== ESTIMATE INFORMATION ====================================== ")

          estimate = call_api('/api/Afe/AfeEstimate', {
            'AuthenticationToken': auth_token,
            'Handle': doc_handle
          })

          print ('Account Num\tIncr\tTotal')
          for lineitem in estimate["LineItems"]:
            accountNumber = lineitem["Account"]["AccountNumber"]
            current_amount = lineitem["Amounts"][-1]['Gross']
            total_amount = 0
            for amount in lineitem['Amounts']:
              total_amount += amount['Gross']
            print ('%s\t%0.2f\t%0.2f' % (accountNumber, current_amount, total_amount))

        finally:
          if auth_token != '':
              call_api('/api/Documents/Close', {'AuthenticationToken': auth_token, 'DocumentHandle': doc_handle})
              print("Closed Handle")

    finally:
        # As a best practise we should always log out once we are done. This finally block does this for us even when
        # an error is encountered.
        if auth_token != '':
            call_api('/api/Authentication/Logout', {'AuthenticationToken': auth_token})
            print("Logged out and released license")


# Run the main program
if __name__ == '__main__':
    main()