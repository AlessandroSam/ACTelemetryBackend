'''
Created on 03 July 2015

@author: DRiVER
Code needs some BIG refactors
'''
from sim_info import SimInfo
import json


# global string constants
MSG_TYPE_STRING     = "type"
MSG_TYPE_DYNAMIC    = "dynamic"
MSG_TYPE_STATIC     = "static"
MSG_TYPE_EMPTY      = "empty"

ACINFO_PHYSICS      = "physics"
ACINFO_GRAPHICS     = "graphics"
ACINFO_STATIC       = "static"

ACSTATIC_acVersion  = "_acVersion"
ACSTATIC_smVersion  = "_smVersion" 


class SimState(object):
    """
    Takes data from SimInfo object (AC SM), analyzes for changes and sends to
    message generator. (Currently contains msgGenerator logic)
    """
    JSON_EMPTY = '{"' + MSG_TYPE_STRING + '":"' + MSG_TYPE_EMPTY + '"}\n'
    packetId = 0

    # JSONs to be sent, static is empty if static_info isn't changed
    static_json = ""
    dynamic_json = ""
    
    # validity flags (currently not checked)
    static_valid = False
    dynamic_valid = False
    
    def __init__(self):
        '''
        Constructor
        '''
        self.info = SimInfo()
        self.static_info = {}
        self.dynamic_info = {}
    # end
    
    def get_static_fields(self):
        """
        Возвращает статические данные из AC (static)
        :return: словарь со статическими данными
        """
        static_dict = {}
        test = getattr(self.info.static, "_smVersion")
        if test == "":
            return None
        for field, type_spec in self.info.static._fields_:
            value = getattr(self.info.static, field)
            if isinstance(value, float):
                value = format(value, ".2f")
            if not isinstance(value, (str, float, int)):
                value = list(value)
                for index in range(0, len(value)):
                    value[index] = format(value[index], ".2f")
            static_dict.update({field: value})
        static_dict.update({MSG_TYPE_STRING: MSG_TYPE_STATIC})
        return static_dict
    
    def get_dynamic_fields(self):
        """
        Возвращает динамические данные из AC (graphics, physics, причём вместе).
        :return: словарь с динамическими данными
        """
        dynamic_dict = {}
        for field, type_spec in self.info.physics._fields_:
            value = getattr(self.info.physics, field)
            if isinstance(value, float):
                value = format(value, ".2f")
            if not isinstance(value, (str, float, int)):
                value = list(value)
                for index in range(0, len(value)):
                    value[index] = format(value[index], ".2f")
            dynamic_dict.update({field : value})
        for field, type_spec in self.info.graphics._fields_:
            value = getattr(self.info.graphics, field)
            if isinstance(value, float):
                value = format(value, ".2f")
            if not isinstance(value, (str, float, int)):
                value = list(value)
                for index in range(0, len(value)):
                    value[index] = format(value[index], ".2f")
            dynamic_dict.update({field : value})
        dynamic_dict.update({MSG_TYPE_STRING : MSG_TYPE_DYNAMIC})
        return dynamic_dict
    # end        
    
    def empty_data(self):
        print("[sim_state] No static info")
        self.static_info = {}  # reset info
        self.dynamic_info = {}
        self.static_json = ""
        self.dynamic_json = ""
    # end
    
    def update(self):
        # Обновляет данные из AC mmap
        # Обновляет структуры static_dict и dynamic_dict вместе с JSON-строками
        # Последние устанавливаются в "" если AC не работает, так что клиент получает "пустое" сообщение
        # Статические данные не меняются в ходе одной игровой сессии.
        tmp_static_info = self.get_static_fields()
        if tmp_static_info is not None: 
            self.static_info.update(tmp_static_info)
            self.static_json = json.dumps(self.static_info) + "\n"
            tmp_dynamic_info = self.get_dynamic_fields()
            if tmp_dynamic_info is not None and tmp_dynamic_info.get("status") != 0:
                self.dynamic_info.update(self.get_dynamic_fields())  # update dynamic info
                self.dynamic_json = json.dumps(self.dynamic_info).replace(' ', '') + "\n"
                self.dynamic_valid = True
            else:
                self.empty_data()
    # end            
    
    def invalidate_dinfo(self):
        self.dynamic_valid = False
