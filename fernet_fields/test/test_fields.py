from datetime import date, datetime

from django.db import connection
from django.utils.encoding import force_bytes, force_text
import pytest

from fernet_fields import fields
from . import models


class TestEncryptedField(object):
    def test_deconstruct(self):
        f = fields.EncryptedTextField(key='secret')

        assert f.deconstruct()[3]['key'] == 'secret'


@pytest.mark.parametrize(
    'model,vals',
    [
        (models.EncryptedText, ['foo', 'bar']),
        (models.EncryptedChar, ['one', 'two']),
        (models.EncryptedEmail, ['a@example.com', 'b@example.com']),
        (models.EncryptedInt, [1, 2]),
        (models.EncryptedDate, [date(2015, 2, 5), date(2015, 2, 8)]),
        (
            models.EncryptedDateTime,
            [datetime(2015, 2, 5, 15), datetime(2015, 2, 8, 16)],
        ),
    ],
)
class TestEncryptedFieldQueries(object):
    def test_insert(self, db, model, vals):
        """Data stored in DB is actually encrypted."""
        model.objects.create(value=vals[0])
        with connection.cursor() as cur:
            cur.execute('SELECT value FROM %s' % model._meta.db_table)
            data = [
                models.fernet.decrypt(force_bytes(r[0]))
                for r in cur.fetchall()
            ]

        coerce = {
            models.EncryptedText: force_text,
            models.EncryptedChar: force_text,
            models.EncryptedEmail: force_text,
            models.EncryptedInt: int,
            models.EncryptedDate: (
                lambda s: datetime.strptime(force_text(s), '%Y-%m-%d').date()),
            models.EncryptedDateTime: (
                lambda s: datetime.strptime(force_text(s), '%Y-%m-%d %H:%M:%S')),
        }[model]

        assert list(map(coerce, data)) == [vals[0]]

    def test_insert_and_select(self, db, model, vals):
        """Data round-trips through insert and select."""
        model.objects.create(value=vals[0])
        found = model.objects.get()

        assert found.value == vals[0]

    def test_update_and_select(self, db, model, vals):
        """Data round-trips through update and select."""
        model.objects.create(value=vals[0])
        model.objects.update(value=vals[1])
        found = model.objects.get()

        assert found.value == vals[1]


def test_nullable(db):
    """Encrypted field can be nullable."""
    models.EncryptedInt.objects.create(value=None)
    found = models.EncryptedInt.objects.get()

    assert found.value is None
