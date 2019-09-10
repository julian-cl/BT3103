# This activity requires Python 2.7 runtime
# -*- coding: utf-8 -*-
import json
import traceback
import logging
import doctest

import re

import signal
import time

    
def lambda_handler(event, context):
    
    def run_local(requestDict):
        #namespace = UsedNamespace()
    
        #Add a try here to catch errors and return a better response
        solution = requestDict['solution']
        tests = requestDict['tests']
    
        import StringIO
        import sys
        # Store App Engine's modified stdout so we can restore it later
        gae_stdout = sys.stdout
        # Redirect stdout to a StringIO object
        new_stdout = StringIO.StringIO()
        sys.stdout = new_stdout

        try:
            namespace = {}
            compiled = compile('import json', 'submitted code', 'exec')
            exec compiled in namespace
            compiled = compile(solution, 'submitted code', 'exec')
            exec compiled in namespace
            namespace['YOUR_SOLUTION'] = solution.strip()
            namespace['LINES_IN_YOUR_SOLUTION'] = len(solution.strip().splitlines())

            test_cases = doctest.DocTestParser().get_examples(tests)
            results, solved = execute_test_cases(test_cases, namespace)
        
            # Get whatever was printed to stdout using the `print` statement (if necessary)
            printed = new_stdout.getvalue()
            # Restore App Engine's original stdout
            sys.stdout = gae_stdout
        
            responseDict = {"solved": solved , "results": results, "printed":printed}
        
            #Add a try here can catch errors. 
            responseJSON = json.dumps(responseDict)
            logging.info("Python verifier returning %s",responseJSON)
            return responseJSON
        except:
            sys.stdout = gae_stdout
            errors = traceback.format_exc()
            logging.info("Python verifier returning errors =%s", errors)
            if len(errors) > 500:
                lines = errors.splitlines()
                i = len(lines) - 1
                errors = lines[i]
                i -= 1
                while i >= 0:
                    line = lines[i]
                    s = '%s\n%s' % (line, errors)
                    if len(s) > 490:
                        break
                    errors = s
                    i -= 1
                errors = '...\n%s' % errors

            responseDict = {'errors': '%s' % errors}
            responseJSON = json.dumps(responseDict)
            #logging.info("######## Returning json encoded errors %s", responseJSON)
            return responseJSON

    #Refactor for better readability.
    def execute_test_cases(testCases, namespace):
        resultList = []
        solved = True
        for e in testCases:
            if not e.want:
                exec e.source in namespace
                continue
            call = e.source.strip()
            logging.warning('call: %s', (call,))
            got = eval(call, namespace)
            expected = eval(e.want, namespace)
        
            correct = True
            if got == expected:
                correct = True
            else:
                correct = False
                solved = False
            resultDict = {'call': call, 'expected': expected, 'received': "%(got)s" % {'got': got}, 'correct': correct}
            resultList.append(resultDict)
        return resultList, solved
    
    method = event.get('httpMethod',{}) 
    
    indexPage = None
    with open("index.html", "r") as f:
        indexPage = f.read()
    
    if method == 'GET':
        return {
            "statusCode": 200,
            "headers": {
            'Content-Type': 'text/html',
            },
            "body": indexPage
        }
        
    if method == 'POST':
        bodyContent = event.get('body',{}) 
        parsedBodyContent = json.loads(bodyContent)
        testCases = parsedBodyContent["shown"]["0"] 
        solution = parsedBodyContent["editable"]["0"] 

        timeout = False
        # handler function that tell the signal module to execute
        # our own function when SIGALRM signal received.
        def timeout_handler(num, stack):
            print("Received SIGALRM")
            raise Exception("processTooLong")

        # register this with the SIGALRM signal    
        signal.signal(signal.SIGALRM, timeout_handler)
        
        # signal.alarm(10) tells the OS to send a SIGALRM after 10 seconds from this point onwards.
        signal.alarm(10)

        # After setting the alarm clock we invoke the long running function.
        try:
            jsonResponse = run_local({"solution": solution, "tests": testCases})
        except Exception as ex:
            if "processTooLong" in ex:
                timeout = True
                print("processTooLong triggered")
        # set the alarm to 0 seconds after all is done
        finally:
            signal.alarm(0)

        jsonResponseData = json.loads(jsonResponse)
        
        solvedStatusText = expectedText = receivedText = callText = textResults = tableContents = ""
        overallResults = """<span class="md-subheading">All tests passed: {0}</span><br/>""".format(str(jsonResponseData.get("solved")))
        numTestCases = len(re.findall('>>>', testCases))
        resultContent = jsonResponseData.get('results') 
        textBackgroundColor = "#ffffff"
        
        if resultContent:
            for i in range(len(resultContent)):
                expectedText = resultContent[i]["expected"]
                receivedText = resultContent[i]["received"]
                correctText = resultContent[i]["correct"]
                callText = resultContent[i]["call"]
                if str(expectedText) == str(receivedText):
                    textResults = textResults + "\nHurray! You have passed the test case. You called {0} and received {1} against the expected value of {2}.\n".format(callText, receivedText, expectedText)
                    textBackgroundColor = "#b2d8b2"
                else:
                    textResults = textResults + "\nThe test case eludes your code so far but try again! You called {0} and received {1} against the expected value of {2}.\n".format(callText, receivedText, expectedText)
                    textBackgroundColor = "#ff9999"
                tableContents = tableContents + """
                <tr bgcolor={4}>
                    <td>{0}</td>
                    <td>{1}</td>
                    <td>{2}</td>
                    <td>{3}</td>
                </tr>
                """.format(callText,expectedText,receivedText,correctText,textBackgroundColor)
        solvedStatusText = str(jsonResponseData.get("solved")) or "error"
        textResults = """All tests passed: {0}\n""".format(solvedStatusText) + textResults
        if not resultContent:
            textResults = "Your test is passing but something is incorrect..."
            
        if timeout or jsonResponseData.get("errors"):
            textResults = "An error - probably related to code syntax - has occured. Do look through the JSON results to understand the cause."
            tableContents = """
                <tr>
                    <td></td>
                    <td></td>
                    <td>error</td>
                    <td></td>
                </tr>
                """
        htmlResults="""
        
        <html>
                <head>
                    <meta charset="utf-8">
                    <meta content="width=device-width,initial-scale=1,minimal-ui" name="viewport">
                </head>
                <body>
                    <div>
                        {0}
                        <span class="md-subheading tableTitle">Tests</span>
                        <table>
                             <thead>
                                <tr>
                                    <th>Called</th>
                                    <th>Expected</th>
                                    <th>Received</th>
                                    <th>Correct</th>
                                </tr>
                            </thead>
                            <tbody>
                                {1}
                            </tbody>
                        </table>
                    </div>
                </body>
                <style>
                br {{
                    display:block;
                    content:"";
                    margin:1rem
                }}
                table{{
                    text-align:center
                }}
                .tableTitle{{
                    text-decoration:underline
                }}
                </style>
            </html>

            """.format(overallResults,tableContents)
        return {
            "statusCode": 200,
            "headers": {
            "Content-Type": "application/json",
                },
            "body":  json.dumps({
                "isComplete":jsonResponseData.get("solved"),
                "jsonFeedback": jsonResponse,
                "htmlFeedback": htmlResults,
                "textFeedback": textResults
            })
            }
