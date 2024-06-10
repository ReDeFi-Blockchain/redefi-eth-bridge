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

    class Meta:
        table_name = 'transfer'
        only_save_dirty = True

    @hybrid_property
    def tx_hash(self):
        return self._tx_hash

    @tx_hash.setter
    def tx_hash(self, value: str):
        value = self.prep_tx_hash(value)
        if len(value) != 64:
            raise ValueError('Invalid tx_hash')
        self._tx_hash = value

    @classmethod
    def prep_tx_hash(cls, tx_hash: str):
        if tx_hash.startswith('0x'):
            return tx_hash[2:].lower()
        return tx_hash.lower()

    @classmethod
    def get_or_create(cls, tx_hash: str):
        tx_hash = cls.prep_tx_hash(tx_hash)
        existed = Transfer.select().where(Transfer.tx_hash == tx_hash).first()
        if not existed:
            return Transfer(_tx_hash=tx_hash)
        return existed