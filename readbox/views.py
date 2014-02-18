from __future__ import unicode_literals
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import authenticate, login, logout
from readbox.forms import RegistrationForm, LoginForm
from readbox.models import UserEx
from readbox.tasks import send_activation_email, get_evernote_client
from manhattan.settings import safe
from itsdangerous import BadSignature
from datetime import datetime, timedelta
from django.utils import simplejson as json
import oauth2 as oauth
import hashlib
import requests
import urlparse

pocket_consumer_key = 'POCKET HERE'
pocket_request = 'https://getpocket.com/v3/oauth/request'
pocket_auth = 'https://getpocket.com/auth/authorize?request_token={0}&redirect_uri={1}'
pocket_redirect_uri = 'https://www.readbox.co/accounts/callbacks/pocket/'
evernote_redirect_uri = 'https://www.readbox.co/accounts/callbacks/evernote/'
readability_consumer_key = 'readbox'
readability_consumer_secret = 'READABILITY HERE'
readability_request_token = 'https://www.readability.com/api/rest/v1/oauth/request_token/'
readability_authorize = 'https://www.readability.com/api/rest/v1/oauth/authorize/?oauth_token={0}&oauth_callback={1}'
readability_redirect_uri = 'https://www.readbox.co/accounts/callbacks/readability/'
readability_token = 'https://www.readability.com/api/rest/v1/oauth/access_token/'


def index_view(request):
    obj = {
        'login_form': LoginForm(),
        'registration_form': RegistrationForm(),
    }
    return render_to_response('manhattan/index.html', obj, context_instance=RequestContext(request))


def login_view(request):
    form = LoginForm(request.POST)
    if request.POST:
        if form.is_valid():
            user = authenticate(username=request.POST['email'], password=request.POST['password'])
            if user is not None:
                login(request, user)
                return HttpResponse()
            else:
                return HttpResponseForbidden()
        else:
            return HttpResponseForbidden()


def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')


def registration_view(request):
    form = RegistrationForm(request.POST)
    if request.POST:
        if form.is_valid():
            if request.POST['password'] < 6:
                return HttpResponseForbidden('The password must be at least 6 characters.')
            if len(UserEx.objects.filter(email=request.POST['email'])) > 0:
                return HttpResponseForbidden('The email address is already in use.')
            new_user = UserEx.objects.create_user(username=request.POST['email'], email=request.POST['email'],
                                                  password=request.POST['password'],
                                                  facebook_name=request.POST['first_name'] + ' ' + request.POST['last_name'],
                                                  picture='http://www.gravatar.com/avatar/' +
                                                        hashlib.md5(str(request.POST['email']).lower()).hexdigest() +
                                                        '?s=100&d=identicon&r=G')
            new_user.is_active = 0
            new_user.save()
            if isinstance(new_user, UserEx):
                send_activation_email(new_user)
                return HttpResponse({'success': True})
            else:
                return HttpResponseForbidden('An error has occurred, please contact us.')
        else:
            return HttpResponseForbidden()


def activation_view(request):
    obj = {
        'activation_message': 'Email Verification was successful. You can now log in.',
        'panel_style': 'panel-success'
    }
    try:
        activation = json.loads(safe.loads(request.GET['c']))
        user_act = UserEx.objects.get(email=activation['email'])
        if 'email' in activation and 'created_at' in activation:
            if user_act and not user_act.is_active:
                if (datetime.utcnow() - datetime.strptime(activation['created_at'] + 'Z', '%Y-%m-%dT%H:%M:%S.%fZ')) > timedelta(days=2):
                    obj['panel_style'] = 'panel-warning'
                    obj['activation_message'] = 'This code verification is expired.'
                else:
                    user_act.is_active = 1
                    user_act.save()
            elif user_act and user_act.is_active:
                obj['panel_style'] = 'panel-warning'
                obj['activation_message'] = 'This email address is already activated.'
            else:
                obj['panel_style'] = 'panel-danger'
                obj['activation_message'] = 'Oh Snap! Something went wrong.'
        else:
            obj['panel_style'] = 'panel-danger'
            obj['activation_message'] = 'Oh Snap! Something went wrong.'
    except (BadSignature, KeyError):
        obj['panel_style'] = 'panel-danger'
        obj['activation_message'] = 'Oh Snap! Something went wrong.'
    return render_to_response('manhattan/activation.html', obj, context_instance=RequestContext(request))


def connect_pocket(request):
    request_token = requests.post(pocket_request, headers={'content-type': 'application/json',
                                                           'x-accept': 'application/json'},
                                  data=json.dumps({'consumer_key': pocket_consumer_key,
                                                   'redirect_uri': pocket_redirect_uri})).json()
    if not request.user.extras:
        request.user.extras = {}
    request.user.extras['pocket'] = request_token
    request.user.save()
    return HttpResponseRedirect(pocket_auth.format(request_token['code'], pocket_redirect_uri))


def callback_pocket(request):
    try:
        res = requests.post('https://getpocket.com/v3/oauth/authorize',
                            headers={'content-type': 'application/json',
                                     'x-accept': 'application/json'},
                            data=json.dumps({'consumer_key': pocket_consumer_key,
                                             'code': request.user.extras['pocket']['code']}))
        if res.status_code == 200:
            access_token = res.json()
        else:
            return 'An error has occured during authentication'
        request.user.extras['pocket'] = access_token['access_token']
        if 'enabled' not in request.user.extras:
            request.user.extras['enabled'] = []
        request.user.extras['enabled'].append('pocket')
        request.user.save()
        return HttpResponseRedirect('/reader/#/settings/?success=true&extra=pocket')
    except KeyError:
        if 'enabled' in request.user.extras:
            request.user.extras['enabled'].remove('pocket')
            request.user.save()
        return HttpResponseRedirect('/reader/#/settings/?success=false&extra=pocket')


def connect_evernote(request):
    client = get_evernote_client()
    request_token = client.get_request_token(evernote_redirect_uri)
    if not request.user.extras:
        request.user.extras = {}
    request.user.extras['evernote'] = request_token
    request.user.save()
    return HttpResponseRedirect(client.get_authorize_url(request_token))


def callback_evernote(request):
    try:
        client = get_evernote_client()
        access_token = client.get_access_token(
            oauth_token=request.user.extras['evernote']['oauth_token'],
            oauth_token_secret=request.user.extras['evernote']['oauth_token_secret'],
            oauth_verifier=request.GET['oauth_verifier'])
        request.user.extras['evernote'] = access_token
        if 'enabled' not in request.user.extras:
            request.user.extras['enabled'] = []
        request.user.extras['enabled'].append('evernote')
        request.user.save()
        return HttpResponseRedirect('/reader/#/settings/?success=true&extra=evernote')
    except KeyError:
        if 'enabled' in request.user.extras:
            request.user.extras['enabled'].remove('evernote')
            request.user.save()
        return HttpResponseRedirect('/reader/#/settings/?success=false&extra=evernote')


def connect_readability(request):
    consumer = oauth.Consumer(readability_consumer_key, readability_consumer_secret)
    client = oauth.Client(consumer)
    resp, token = client.request(readability_request_token, method="GET")
    if resp['status'] != '200':
        return HttpResponseRedirect('/reader/#/settings/?success=false&extra=readability')
    access_token = dict(urlparse.parse_qsl(token))
    if not request.user.extras:
        request.user.extras = {}
    request.user.extras['readability'] = access_token
    request.user.save()
    return HttpResponseRedirect(readability_authorize.format(access_token['oauth_token'], readability_redirect_uri))


def callback_readability(request):
    consumer = oauth.Consumer(readability_consumer_key, readability_consumer_secret)
    token = oauth.Token(request.user.extras['readability']['oauth_token'],
                        request.user.extras['readability']['oauth_token_secret'])
    token.set_verifier(request.GET['oauth_verifier'])
    client = oauth.Client(consumer, token)
    resp, content = client.request(readability_token, method='POST')
    if resp['status'] != '200':
        if 'enabled' in request.user.extras and 'readability' in request.user.extras['enabled']:
            del request.user.extras['enabled']['readability']
            request.user.save()
        return HttpResponseRedirect('/reader/#/settings/?success=false&extra=readability')
    access_token = dict(urlparse.parse_qsl(content))
    if not request.user.extras:
        request.user.extras = {}
    request.user.extras['readability'] = access_token
    if 'enabled' not in request.user.extras:
            request.user.extras['enabled'] = []
    request.user.extras['enabled'].append('readability')
    request.user.save()
    return HttpResponseRedirect('/reader/#/settings/?success=true&extra=readability')