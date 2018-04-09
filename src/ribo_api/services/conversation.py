from django.db import transaction
from django.utils import timezone
from datetime import datetime
from ribo_api.const import TaskType, Recurrence, weekday, TypeRepeat
from ribo_api.models.message import Message, ContentMessage
from ribo_api.serializers.message import ContentMessageSerializer, MessageSerializer
from ribo_api.services.base import BaseService
from ribo_api.services.dialogflow import DialogFlow, ApiAIService
from ribo_api.services.task import TaskService
from ribo_api.services.utils import Utils
from ribo_api.string import MSG_STRING


class ConversationService(BaseService):

    @classmethod
    def load_messages(cls, user_id, **kwargs):
        limit = kwargs.get("limit",20)
        page = kwargs.get("page",0)
        offset = limit*page
        messages = Message.objects(user_id=user_id).order_by("-id")[offset:offset+limit]
        return MessageSerializer(messages, many=True).data

    @classmethod
    def reply(cls, data, **kwargs):
        user_id = data.get("user_id",0)
        body = data.get("body","")
        is_question = False
        messages = []
        if body:
            with transaction.atomic():
                try:
                    message = Message.objects(user_id=user_id).order_by("-id")[0]
                    if message['content']['answer_text']:
                        message = Message()
                        message['user_id'] = user_id
                        message.content = ContentMessage(question_text=body, answer_text='', from_who=1)
                        message['action'] = None
                        message['next_question_id'] = None
                        message.save()
                    else:
                        is_question = False
                        next_question = None
                        if is_question:
                            pass
                        message = cls.save_user_message(body, user_id, data, is_question, next_question)
                    result = cls.process_reply(user_id,body, message)
                    response = result['response']
                    if is_question:
                        message = cls.save_user_message(response, user_id, data, False)
                    else:
                        message = cls.create_message(response, user_id, result, 0)
                        if result.get('finish',False):
                            text = MSG_STRING.NEED_RIBO
                            message2 = cls.create_message(text, user_id, result, 0)
                            messages.append(message2)
                    messages.append(message)
                    return reversed(messages)
                except Exception as e:
                    raise e


    @classmethod
    def save_user_message(cls, body, user_id, data, is_question=False, next_question=None,**kwargs):
        if is_question:
            message = Message()
            message['user_id'] = user_id
            message.content = ContentMessage(question_text=body, answer_text='',from_who=1)
            message['action'] = None
            message['next_question_id'] = None
            if next_question:
                message.next_question_id = next_question.id
        else:
            message = Message.objects(user_id=user_id).order_by("-id")[0]
            message['content']['answer_text'] = body
            message['updated_at'] = timezone.now()
        message.save()
        return message

    @classmethod
    def create_message(cls, text, user_id, data, next_question, **kwargs):
        message = Message()
        message['user_id'] = user_id
        message.content = ContentMessage(question_text=text, answer_text='', from_who=0)
        message['action'] = data.get('action','')
        message['next_question_id'] = None
        if next_question:
            message.next_question_id = next_question.id
        message.save()
        return message


    @classmethod
    def process_reply(cls,user_id, text, message):
        ai_result = ApiAIService.get_result(user_id,text)
        params = ai_result['parameters']
        action = ai_result['action']
        fulfillment = ai_result['fulfillment']
        response = fulfillment.get('speech','')
        result = None
        finish = False
        if 'reminder' in action:
            if action == 'reminders.add':
                task_data = {
                    'user_id': user_id,
                }
                date_time = params.get('date-time', [])
                name = params.get('name', '')
                recurrences = params.get('recurrence', [])
                date_time = datetime.strptime(date_time[0], '%Y-%m-%dT%H:%M:%S.000Z')
                if recurrences and recurrences[0] != Recurrence.RECURRENCE_NONE:
                    date_time = cls.get_datetime(params, date_time)
                if date_time:
                    task_data['at_time'] = []
                    for date in date_time:
                        task_data['at_time'].append(date)
                if name:
                    task_data['title'] = name
                    if 'call' in name:
                        task_data['type'] = TaskType.CALL
                    elif 'email' in name:
                        task_data['type'] = TaskType.EMAIL
                if name and date_time and recurrences:
                    task_data['recurrence'] = recurrences
                    result = TaskService.create_task(data=task_data)
                    finish = True
            elif action == 'reminders.get':
                query_data = { 'user_id': user_id}
                date = params.get('date','')
                time = params.get('time','')
                name = params.get('name','')
                if date and time:
                    query_data['at_time'] = date + time
                if name:
                    query_data['title'] = name
                result = TaskService.get_task(query_data)
                finish = True
            elif action == 'reminders.reschedule':
                pass
            elif action == 'reminders.remove':
                pass
            elif action == 'reminders.rename':
                pass

        elif 'event' in action:
            pass
        message['action'] = action
        message.save()
        data = {
            'response' : response,
            'finish': finish,
            'result' : result
        }
        return data


    @classmethod
    def get_datetime(cls,data, date_time):
        recurrences = data.get('recurrence', '')
        for _recur in recurrences:
            if _recur in Recurrence.RECURRENCE_WEEKLY:
                date_number = weekday[_recur]
                date_time.append(Utils.next_weekday(date_number))
            elif _recur == Recurrence.RECURRENCE_WEEKENDS:
                date_time.append(Utils.next_weekday(weekday['sat']))
                date_time.append(Utils.next_weekday(weekday['sun']))
        return date_time


