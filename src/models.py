import peewee
from playhouse.hybrid import hybrid_property

db = peewee.DatabaseProxy()


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Transfer(BaseModel):
    sender_chain_id = peewee.IntegerField(index=True)
    deposit_event_block_id = peewee.IntegerField(default=0)
    receiver_chain_id = peewee.IntegerField(index=True)
    listed_event_block_id = peewee.IntegerField(default=0)
    validator_confirmations = peewee.IntegerField(default=0)
    _tx_hash = peewee.CharField(max_length=64, index=True)

    @hybrid_property
    def tx_hash(self):
        return self._tx_hash

    @tx_hash.setter
    def tx_hash(self, value: str):
        if value.startswith('0x'):
            value = value[2:]
        if len(value) != 64:
            raise ValueError('Invalid tx_hash')
