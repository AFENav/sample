# Created using Python 2.7.7
from urllib2 import Request, urlopen, URLError, HTTPError
from json import loads, dumps
import datetime
import re
import csv
import sys

# the base_url will be the url to your service machine
# base_url = 'https://server:14101'
base_url = 'https://e258-mdd:8082'


def call_api(url, request_data):
    """ Sends our request to the service and returns the data asked for"""
    req_object = Request(base_url + url, dumps(request_data))
    # We need to set the header of each our request to make sure it sends json
    req_object.add_header('Content-Type', 'application/json')
    try:
        # 10 second time out may need to be adjusted for your environment
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
        result = call_api('/api/Authentication/Login',
                          {'UserName': 'System Admin',
                           'Password': '1'})

        # once logged in, we get an authentication token back from the service.
        # auth tokens are needed for almost all API requests
        auth_token = result['AuthenticationToken']

        # Here we are using the browse page API call to filter the AFEs
        result = call_api('/api/Documents/Summary',
                          {'Type': 'AFE',
                           'Echo': '',
                           'TopLevelSearch': '',
                           'BaseFilter': 'AllAFEs',
                           # The 'ColumnIds' properties lets us choose the data we want to receive from the service
                           'ColumnIds': [{'Id': 'AFENUMBER_DOC/AFENUMBER'},
                                         {'Id': 'STATUS'},
                                         {'Id': 'VERSION_STRING'},
                                         # Notice the added filter property on this ColumnId object.
                                         # Filter properties can apply to more than one column at a time.
                                         {'Id': 'DESCRIPTION', 'Filter': 'AFE'},
                                         {'Id': 'CLOSED'},
                                         {'Id': 'PAA_AFE_TYPE'},
                                         {'Id': 'CREATION_DATE'}],
                           'ColumnSorts': [{'Id': 'AFENUMBER_DOC/AFENUMBER', 'SortAscending': True}],
                           'AuthenticationToken': auth_token})

        # The doc_list variable now contains an array of rows, each of which has two objects.
        # The first is the AFE GUID that can be used in further API calls to get more detail.
        # The second object contains the data we requested in the 'ColumnIds' property.
        doc_list = result['Rows']
        record_count = result['FilteredRecordCount']
        total_count = result['TotalRecordCount']
        writer = csv.writer(sys.stdout)

        print 'Id (GUID), AFE Number, Status, Version, Description, Closed, AFE Type, Creation Date'
        for row in doc_list:
            row_list = row['Row']
            row_list.insert(0, row['Id'])
            writer.writerow(row_list)

        print 'Listing ' + str(record_count) + ' of ' + str(total_count)

        # now we loop through each AFE and change the description
        for row in doc_list:
            # Its always a good idea to open documents in a try block, that way we can print a good error message
            # and skip processing the document if it wont open for us.
            doc_id = row["Id"]
            try:
                # open each document
                result = call_api('/api/Documents/Open',
                                  {'DocumentType': 'AFE',
                                   'DocumentId': doc_id,
                                   # The AutoCommit property tells the service whether it should save the document on
                                   # connection loss. For non user facing processes (like this program) it should
                                   # be set to false since we don't want to have to deal with half saved changes.
                                   'AutoCommit': False,
                                   'AuthenticationToken': auth_token})
            except HTTPError:
                print 'Failed to open document ' + doc_id + '. No changes were made to the document.'
                continue

            try:
                # At this point the document is open.  We use a try finally block here to make sure we don't leave any
                # documents locked in the open state.

                # document handles are needed for all API requests that perform actions on a document
                doc_handle = result['DocumentHandle']
                # get the description field
                result = call_api('/api/Documents/ReadFieldAsText',
                                  {'DocumentHandle': doc_handle,
                                   'AuthenticationToken': auth_token,
                                   'Path': 'DESCRIPTION'})
                description = result['TextValue']

                # capitalize all instances of 'AFE' in the description
                regex = re.compile(re.escape('afe'), re.IGNORECASE)
                new_description = regex.sub('AFE', description)

                # update the AFE

                call_api('/api/Documents/Field/UpdateText',
                         {'FieldPath': '',
                          'FieldName': 'DESCRIPTION',
                          'FieldValue': new_description,
                          'DocumentHandle': doc_handle,
                          'AuthenticationToken': auth_token})

                # save the afe
                call_api('/api/Documents/Save',
                         # The 'Comment' and 'Source' properties will show up on the change tracking tab for the
                         # document being edited.  Be sure to set them to something meaningful so you can keep track of
                         # changes done by your scripts.
                         {'Comment': 'Edited by script',
                          'Source': 'Filter_AFE_on_description.py',
                          'DocumentHandle': doc_handle,
                          'AuthenticationToken': auth_token})

            finally:
                # No matter what happens, we need to close the document we opened.  Open documents are not editable by
                # users so we never want te leave them in that state.
                call_api('/api/Documents/Close',
                         {'DocumentHandle': doc_handle,
                          'AuthenticationToken': auth_token})
    finally:
        # As a best practise we should always log out once we are done. This finally block does this for us even when
        # an error is encountered.
        if auth_token != '':
            call_api('/api/Authentication/Logout',
                     {'AuthenticationToken': auth_token})


# Run the main program
if __name__ == '__main__':
    main()