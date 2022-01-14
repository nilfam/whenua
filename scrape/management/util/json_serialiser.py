import datetime
import json


class MongoDateEncoder(json.JSONEncoder):
     def default(self, obj):
         if isinstance(obj, datetime.datetime):
             obj_as_dict = {"$date": obj.strftime('%Y-%m-%dT%H:%M:%SZ')}
             return json.dumps(obj_as_dict)
         return json.JSONEncoder.default(self, obj)


def serialise_array(arr):
    arr_json = []
    for obj in arr:
        obj_json = json.dumps(obj, cls=MongoDateEncoder)
        obj_json = obj_json.replace('"ISODate(((', 'ISODate("').replace(')))ISODate"', '")')
        arr_json.append(obj_json)

    return '[' + ','.join(arr_json) + ']'


if __name__ == '__main__':
    person = dict(name='John Doe', dob=datetime.datetime(1987, 8, 16))

    print(json.dumps([person], cls=MongoDateEncoder))