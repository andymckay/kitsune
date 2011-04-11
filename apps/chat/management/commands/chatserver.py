from django.core.management.base import BaseCommand

from tornado.web import Application
from tornad_io import SocketIOHandler, SocketIOServer


clients = {}


class ChatHandler(SocketIOHandler):
    def on_open(self, *args, **kwargs):
        if not self.session.id in clients:
            clients.update({self.session.id: self})
            self.send('Welcome!')
            for i in clients:
                if i != self.session.id:
                    clients[i].send('%s joined!' % self.session.id)

    def on_message(self, message):
        import pdb; pdb.set_trace()
        for i in clients:
            clients[i].send(message)

    def on_close(self):
        clients.pop(self.session.id, None)
        for i in clients:
            clients[i].send('%s has left!' % self.session.id)

chatroute = ChatHandler.routes('socket.io/*')

app = Application(
    [chatroute],
    enabled_protocols = ['websocket', 'flashsocket', 'xhr-multipart',
                         'xhr-polling', 'jsonp-polling'],
    flash_policy_port=8043,
    socket_io_port = 9000,
)


class Command(BaseCommand):
    help = 'Start a chat server pool.'

    def handle(self, *args, **options):
        """Oh god oh god oh god."""
        SocketIOServer(app)
