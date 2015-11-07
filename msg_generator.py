'''
Created on 03 july 2015

@author: DRiVER
'''
import json

class MessageGenerator(object):
    '''
    Generates JSON message based on given type and data dictionary
    '''
    msg_type_string = "type"

#    def __init__(self, params):
#        '''
#        Constructor
#        '''
    def create_message(self, msgtype, msgdict):
        result = json.dumps({self.msg_type_string : msgtype})
        result += json.dumps(msgdict)
        result += "\n"
        return result
               
        
