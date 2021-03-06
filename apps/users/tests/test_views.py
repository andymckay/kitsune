from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail

import mock
from nose.tools import eq_
from pyquery import PyQuery as pq
from tidings.tests import watch

from questions.models import Question, CONFIRMED, UNCONFIRMED
from sumo.tests import TestCase, LocalizingClient
from sumo.urlresolvers import reverse
from sumo.tests import send_mail_raise_smtp
from users.models import RegistrationProfile, EmailChange
from users import ERROR_SEND_EMAIL


class RegisterTests(TestCase):
    fixtures = ['users.json']

    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.client.logout()

    def tearDown(self):
        settings.DEBUG = self.old_debug

    @mock.patch.object(Site.objects, 'get_current')
    def test_new_user(self, get_current):
        get_current.return_value.domain = 'su.mo.com'
        response = self.client.post(reverse('users.register', locale='en-US'),
                                    {'username': 'newbie',
                                     'email': 'newbie@example.com',
                                     'password': 'foo',
                                     'password2': 'foo'}, follow=True)
        eq_(200, response.status_code)
        u = User.objects.get(username='newbie')
        assert u.password.startswith('sha256')
        assert not u.is_active
        eq_(1, len(mail.outbox))
        assert mail.outbox[0].subject.find('Please confirm your') == 0
        key = RegistrationProfile.objects.all()[0].activation_key
        assert mail.outbox[0].body.find('activate/%s' % key) > 0

        # Now try to log in
        u.is_active = True
        u.save()
        response = self.client.post(reverse('users.login', locale='en-US'),
                                    {'username': 'newbie',
                                     'password': 'foo'}, follow=True)
        eq_(200, response.status_code)
        eq_('http://testserver/en-US/home', response.redirect_chain[0][0])

    @mock.patch.object(mail, 'send_mail')
    @mock.patch.object(Site.objects, 'get_current')
    def test_new_user_smtp_error(self, get_current, send_mail):
        get_current.return_value.domain = 'su.mo.com'

        send_mail.side_effect = send_mail_raise_smtp
        response = self.client.post(reverse('users.register', locale='en-US'),
                                    {'username': 'newbie',
                                     'email': 'newbie@example.com',
                                     'password': 'foo',
                                     'password2': 'foo'}, follow=True)
        self.assertContains(response, unicode(ERROR_SEND_EMAIL))
        assert not User.objects.filter(username='newbie').exists()

    @mock.patch.object(Site.objects, 'get_current')
    def test_unicode_password(self, get_current):
        u_str = u'\xe5\xe5\xee\xe9\xf8\xe7\u6709\u52b9'
        get_current.return_value.domain = 'su.mo.com'
        response = self.client.post(reverse('users.register', locale='ja'),
                                    {'username': 'cjkuser',
                                     'email': 'cjkuser@example.com',
                                     'password': u_str,
                                     'password2': u_str}, follow=True)
        eq_(200, response.status_code)
        u = User.objects.get(username='cjkuser')
        u.is_active = True
        u.save()
        assert u.password.startswith('sha256')

        # make sure you can login now
        response = self.client.post(reverse('users.login', locale='ja'),
                                    {'username': 'cjkuser',
                                     'password': u_str}, follow=True)
        eq_(200, response.status_code)
        eq_('http://testserver/ja/home', response.redirect_chain[0][0])

    @mock.patch.object(Site.objects, 'get_current')
    def test_new_user_activation(self, get_current):
        get_current.return_value.domain = 'su.mo.com'
        user = RegistrationProfile.objects.create_inactive_user(
            'sumouser1234', 'testpass', 'sumouser@test.com')
        assert not user.is_active
        key = RegistrationProfile.objects.all()[0].activation_key
        url = reverse('users.activate', args=[key])
        response = self.client.get(url, follow=True)
        eq_(200, response.status_code)
        user = User.objects.get(pk=user.pk)
        assert user.is_active

    @mock.patch.object(Site.objects, 'get_current')
    def test_new_user_claim_watches(self, get_current):
        """Claim user watches upon activation."""
        watch(email='sumouser@test.com', save=True)

        get_current.return_value.domain = 'su.mo.com'
        user = RegistrationProfile.objects.create_inactive_user(
            'sumouser1234', 'testpass', 'sumouser@test.com')
        key = RegistrationProfile.objects.all()[0].activation_key
        self.client.get(reverse('users.activate', args=[key]), follow=True)

        # Watches are claimed.
        assert user.watch_set.exists()

    @mock.patch.object(Site.objects, 'get_current')
    def test_new_user_with_questions(self, get_current):
        """Unconfirmed questions get confirmed with account confirmation."""
        get_current.return_value.domain = 'su.mo.com'
        # TODO: remove this test once we drop unconfirmed questions.
        user = RegistrationProfile.objects.create_inactive_user(
            'sumouser1234', 'testpass', 'sumouser@test.com')

        # Before we activate, let's create a question.
        q = Question.objects.create(title='test_question', creator=user,
                                    content='test', status=UNCONFIRMED,
                                    confirmation_id='$$$')

        # Activate account.
        key = RegistrationProfile.objects.all()[0].activation_key
        url = reverse('users.activate', args=[key])
        response = self.client.get(url, follow=True)
        eq_(200, response.status_code)

        q = Question.objects.get(creator=user)
        # Question is listed on the confirmation page.
        assert 'test_question' in response.content
        assert q.get_absolute_url() in response.content
        eq_(CONFIRMED, q.status)

    def test_duplicate_username(self):
        response = self.client.post(reverse('users.register', locale='en-US'),
                                    {'username': 'jsocol',
                                     'email': 'newbie@example.com',
                                     'password': 'foo',
                                     'password2': 'foo'}, follow=True)
        self.assertContains(response, 'already exists')

    def test_duplicate_email(self):
        User.objects.create(username='noob', email='noob@example.com').save()
        response = self.client.post(reverse('users.register', locale='en-US'),
                                    {'username': 'newbie',
                                     'email': 'noob@example.com',
                                     'password': 'foo',
                                     'password2': 'foo'}, follow=True)
        self.assertContains(response, 'already exists')

    def test_no_match_passwords(self):
        response = self.client.post(reverse('users.register', locale='en-US'),
                                    {'username': 'newbie',
                                     'email': 'newbie@example.com',
                                     'password': 'foo',
                                     'password2': 'bar'}, follow=True)
        self.assertContains(response, 'must match')


class ChangeEmailTestCase(TestCase):
    fixtures = ['users.json']

    def setUp(self):
        self.client = LocalizingClient()

    def test_redirect(self):
        """Test our redirect from old url to new one."""
        response = self.client.get(reverse('users.old_change_email',
                                           locale='en-US'), follow=False)
        eq_(301, response.status_code)
        eq_('http://testserver/en-US/users/change_email', response['location'])

    @mock.patch.object(Site.objects, 'get_current')
    def test_user_change_email(self, get_current):
        """Send email to change user's email and then change it."""
        get_current.return_value.domain = 'su.mo.com'

        self.client.login(username='pcraciunoiu', password='testpass')
        # Attempt to change email.
        response = self.client.post(reverse('users.change_email'),
                                    {'email': 'paulc@trololololololo.com'},
                                    follow=True)
        eq_(200, response.status_code)

        # Be notified to click a confirmation link.
        eq_(1, len(mail.outbox))
        assert mail.outbox[0].subject.find('Please confirm your') == 0
        ec = EmailChange.objects.all()[0]
        assert ec.activation_key in mail.outbox[0].body
        eq_('paulc@trololololololo.com', ec.email)

        # Visit confirmation link to change email.
        response = self.client.get(reverse('users.confirm_email',
                                           args=[ec.activation_key]))
        eq_(200, response.status_code)
        u = User.objects.get(username='pcraciunoiu')
        eq_('paulc@trololololololo.com', u.email)

    def test_user_change_email_same(self):
        """Changing to same email shows validation error."""
        self.client.login(username='rrosario', password='testpass')
        user = User.objects.get(username='rrosario')
        user.email = 'valid@email.com'
        user.save()
        response = self.client.post(reverse('users.change_email'),
                                    {'email': user.email})
        eq_(200, response.status_code)
        doc = pq(response.content)
        eq_('This is your current email.', doc('ul.errorlist').text())

    def test_user_change_email_duplicate(self):
        """Changing to same email shows validation error."""
        self.client.login(username='rrosario', password='testpass')
        email = 'newvalid@email.com'
        User.objects.filter(username='pcraciunoiu').update(email=email)
        response = self.client.post(reverse('users.change_email'),
                                    {'email': email})
        eq_(200, response.status_code)
        doc = pq(response.content)
        eq_('A user with that email address already exists.',
            doc('ul.errorlist').text())

    @mock.patch.object(Site.objects, 'get_current')
    def test_user_confirm_email_duplicate(self, get_current):
        """If we detect a duplicate email when confirming an email change,
        don't change it and notify the user."""
        get_current.return_value.domain = 'su.mo.com'
        self.client.login(username='rrosario', password='testpass')
        old_email = User.objects.get(username='rrosario').email
        new_email = 'newvalid@email.com'
        response = self.client.post(reverse('users.change_email'),
                                    {'email': new_email})
        eq_(200, response.status_code)
        assert mail.outbox[0].subject.find('Please confirm your') == 0
        ec = EmailChange.objects.all()[0]

        # Before new email is confirmed, give the same email to a user
        User.objects.filter(username='pcraciunoiu').update(email=new_email)

        # Visit confirmation link and verify email wasn't changed.
        response = self.client.get(reverse('users.confirm_email',
                                           args=[ec.activation_key]))
        eq_(200, response.status_code)
        doc = pq(response.content)
        eq_('Unable to change email for user rrosario',
            doc('#main h1').text())
        u = User.objects.get(username='rrosario')
        eq_(old_email, u.email)
