from polymorphic.tests.models import Duck, PurpleHeadDuck


def test_transmogrify_with_init(db):
    pur = PurpleHeadDuck.objects.create()
    assert pur.color == "blue"
    assert pur.home == "Duckburg"

    pur = Duck.objects.get(id=pur.id)
    assert pur.color == "blue"
    # issues/615 fixes following line:
    assert pur.home == "Duckburg"
