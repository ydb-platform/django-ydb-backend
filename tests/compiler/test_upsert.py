from django.test import TransactionTestCase

from .models import NFTToken


class NFTTokenUpsertTest(TransactionTestCase):
    def setUp(self):
        self.token1_data = {
            "contract_address": "0x1a2b3c4d5e",
            "token_id": "12345",
            "owner": "0xAlice123",
            "metadata_url": "ipfs://QmXyZ123",
            "last_price": 1.5
        }
        self.token2_data = {
            "contract_address": "0x1a2b3c4d5d",
            "token_id": "12346",
            "owner": "0xBob450",
            "metadata_url": "ipfs://QmXyZ456r04",
            "last_price": 5.7
        }

    def test_insert_new_token(self):
        NFTToken.objects.upsert(self.token1_data)
        self.assertEqual(NFTToken.objects.count(), 1)

        db_token = NFTToken.objects.get(token_id="12345")
        self.assertEqual(db_token.contract_address, "0x1a2b3c4d5e")
        self.assertEqual(db_token.owner, "0xAlice123")
        self.assertEqual(db_token.metadata_url, "ipfs://QmXyZ123")
        self.assertEqual(db_token.last_price, 1.5)

    def test_update_existing_token(self):
        NFTToken.objects.create(**self.token1_data)

        update_data = {
            "token_id": "12345",
            "contract_address": "0x1a2b3c4d5e",
            "owner": "0xBob456",
            "last_price": 2.5,
            "metadata_url": "ipfs://QmXyZ456"
        }
        NFTToken.objects.upsert(update_data)
        self.assertEqual(NFTToken.objects.count(), 1)

        db_token = NFTToken.objects.get(token_id="12345")
        self.assertEqual(db_token.owner, "0xBob456")
        self.assertEqual(db_token.last_price, 2.5)
        self.assertEqual(db_token.metadata_url, "ipfs://QmXyZ456")

    def test_upsert_without_changes(self):
        NFTToken.objects.upsert(self.token1_data)
        self.assertEqual(NFTToken.objects.count(), 1)

        NFTToken.objects.upsert(self.token1_data)
        self.assertEqual(NFTToken.objects.count(), 1)

        db_token = NFTToken.objects.get(token_id="12345")
        self.assertEqual(db_token.owner, "0xAlice123")
        self.assertEqual(db_token.metadata_url, "ipfs://QmXyZ123")

        self.assertEqual(
            NFTToken.objects.filter(metadata_url="ipfs://QmXyZ123").count(),
            1
        )

    def test_bulk_upsert(self):
        NFTToken.objects.create(
            contract_address="0x1111111111",
            token_id="100",
            owner="0xOwner1",
            metadata_url="ipfs://QmA",
            last_price=10.0,
        )
        NFTToken.objects.create(
            contract_address="0x2222222222",
            token_id="200",
            owner="0xOwner2",
            metadata_url="ipfs://QmB",
            last_price=20.0,
        )
        NFTToken.objects.create(
            contract_address="0x3333333333",
            token_id="300",
            owner="0xOwner3",
            metadata_url="ipfs://QmC",
            last_price=30.0,
        )

        update_data = [
            {
                "contract_address": "0x1111111111",
                "token_id": "100",
                "owner": "0xNewOwner1",
                "metadata_url": "ipfs://QmA",
                "last_price": 15.0
            },
            {
                "contract_address": "0x2222222222",
                "token_id": "200",
                "owner": "0xOwner2",
                "metadata_url": "ipfs://QmB",
                "last_price": 25.0
            },
            {
                "contract_address": "0x4444444444",
                "token_id": "400",
                "owner": "0xOwner4",
                "metadata_url": "ipfs://QmD",
                "last_price": 40.0
            },
            {
                "contract_address": "0x3333333333",
                "token_id": "300",
                "owner": "0xOwner3",
                "metadata_url": "ipfs://QmC",
                "last_price": 30.0,
            }
        ]

        results = NFTToken.objects.bulk_upsert(update_data)
        self.assertEqual(NFTToken.objects.count(), 4)

        updated_token1 = NFTToken.objects.get(token_id="100")
        self.assertEqual(updated_token1.contract_address, "0x1111111111")
        self.assertEqual(updated_token1.metadata_url, "ipfs://QmA")
        self.assertEqual(updated_token1.owner, "0xNewOwner1")
        self.assertEqual(updated_token1.last_price, 15.0)

        updated_token2 = NFTToken.objects.get(token_id="200")
        self.assertEqual(updated_token2.contract_address, "0x2222222222")
        self.assertEqual(updated_token2.last_price, 25.0)
        self.assertEqual(updated_token2.owner, "0xOwner2")
        self.assertEqual(updated_token2.metadata_url, "ipfs://QmB")

        unchanged_token3 = NFTToken.objects.get(token_id="300")
        self.assertEqual(unchanged_token3.owner, "0xOwner3")
        self.assertEqual(unchanged_token3.metadata_url, "ipfs://QmC")
        self.assertEqual(unchanged_token3.contract_address, "0x3333333333")
        self.assertEqual(unchanged_token3.last_price, 30.0)

        new_token4 = NFTToken.objects.get(token_id="400")
        self.assertEqual(new_token4.contract_address, "0x4444444444")
        self.assertEqual(new_token4.owner, "0xOwner4")
        self.assertEqual(new_token4.last_price, 40.0)
        self.assertEqual(new_token4.metadata_url, "ipfs://QmD")

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].token_id, "100")
        self.assertEqual(results[1].token_id, "200")
        self.assertEqual(results[2].token_id, "400")
        self.assertEqual(results[3].token_id, "300")

    def test_bulk_upsert_with_model_instances(self):
        NFTToken.objects.create(
            contract_address="0xAAAAAAA111",
            token_id="101",
            owner="0xAlice",
            metadata_url="ipfs://QmX1",
            last_price=100.0
        )
        NFTToken.objects.create(
            contract_address="0xBBBBBBB222",
            token_id="202",
            owner="0xBob",
            metadata_url="ipfs://QmX2",
            last_price=200.0
        )
        NFTToken.objects.create(
            contract_address="0xCCCCCCC333",
            token_id="303",
            owner="0xCharlie",
            metadata_url="ipfs://QmX3",
            last_price=300.0
        )

        update_data = [
            NFTToken(
                contract_address="0xAAAAAAA1115",
                token_id="101",
                owner="0xAliceUpdated",
                metadata_url="ipfs://QmX1Updated",
                last_price=150.0
            ),
            NFTToken(
                contract_address="0xBBBBBBB222",
                token_id="202",
                owner="0xBobx",
                metadata_url="ipfs://QmX2",
                last_price=250.0
            ),
            NFTToken(
                contract_address="0xDDDDDDD444",
                token_id="404",
                owner="0xDave",
                metadata_url="ipfs://QmX4",
                last_price=400.0
            ),
            NFTToken(
                contract_address="0xCCCCCCC333",
                token_id="303",
                owner="0xCharlie",
                metadata_url="ipfs://QmX3",
                last_price=300.0
            )
        ]

        results = NFTToken.objects.bulk_upsert(update_data)
        self.assertEqual(NFTToken.objects.count(), 4)

        updated_token1 = NFTToken.objects.get(token_id="101")
        self.assertEqual(updated_token1.owner, "0xAliceUpdated")
        self.assertEqual(updated_token1.contract_address, "0xAAAAAAA1115")
        self.assertEqual(updated_token1.metadata_url, "ipfs://QmX1Updated")
        self.assertEqual(updated_token1.last_price, 150.0)

        updated_token2 = NFTToken.objects.get(token_id="202")
        self.assertEqual(updated_token2.contract_address, "0xBBBBBBB222")
        self.assertEqual(updated_token2.last_price, 250.0)
        self.assertEqual(updated_token2.owner, "0xBobx")
        self.assertEqual(updated_token2.metadata_url, "ipfs://QmX2")

        unchanged_token3 = NFTToken.objects.get(token_id="303")
        self.assertEqual(unchanged_token3.contract_address, "0xCCCCCCC333")
        self.assertEqual(unchanged_token3.owner, "0xCharlie")
        self.assertEqual(unchanged_token3.last_price, 300.0)
        self.assertEqual(unchanged_token3.metadata_url, "ipfs://QmX3")

        new_token4 = NFTToken.objects.get(token_id="404")
        self.assertEqual(new_token4.contract_address, "0xDDDDDDD444")
        self.assertEqual(new_token4.owner, "0xDave")
        self.assertEqual(new_token4.metadata_url, "ipfs://QmX4")
        self.assertEqual(new_token4.last_price, 400.0)

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].token_id, "101")
        self.assertEqual(results[1].token_id, "202")
        self.assertEqual(results[2].token_id, "404")
        self.assertEqual(results[3].token_id, "303")
