import pytest
import numpy
from thinc.api import CategoricalCrossentropy, SequenceCategoricalCrossentropy
from thinc.api import L2Distance, CosineDistance
from thinc import registry

# some simple arrays
scores0 = numpy.zeros((3, 3), dtype="f")
labels0 = numpy.asarray([0, 1, 1], dtype="i")

# a few more diverse ones to test realistic values
guesses1 = numpy.asarray([[0.1, 0.5, 0.6], [0.4, 0.6, 0.3], [1, 1, 1], [0, 0, 0]])
labels1 = numpy.asarray([2, 1, 0, 2])
labels1_full = numpy.asarray([[0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]])

guesses2 = numpy.asarray([[0.2, 0.3]])
labels2 = numpy.asarray([1])

eps = 0.0001


def test_loss():
    d_scores = CategoricalCrossentropy().get_grad(scores0, labels0)
    assert d_scores.dtype == "float32"
    assert d_scores.shape == scores0.shape
    d_scores = SequenceCategoricalCrossentropy().get_grad([scores0], [labels0])
    assert d_scores[0].dtype == "float32"
    assert d_scores[0].shape == scores0.shape
    assert SequenceCategoricalCrossentropy().get_grad([], []) == []


@pytest.mark.parametrize(
    "dist", [CategoricalCrossentropy(), CosineDistance(ignore_zeros=True), L2Distance()]
)
@pytest.mark.parametrize("vect", [scores0, guesses1, guesses2])
def test_equality(dist, vect):
    assert int(dist.get_grad(vect, vect)[0][0]) == pytest.approx(0, eps)
    assert dist.get_loss(vect, vect) == pytest.approx(0, eps)


@pytest.mark.parametrize(
    "guesses, labels", [(guesses1, labels1), (guesses1, labels1_full)]
)
def test_categorical_crossentropy(guesses, labels):
    d_scores = CategoricalCrossentropy(normalize=True).get_grad(guesses, labels)
    assert d_scores.shape == guesses.shape

    # The normalization divides the difference (e.g. 0.4) by the number of vectors (4)
    assert d_scores[1][0] == pytest.approx(0.1, eps)
    assert d_scores[1][1] == pytest.approx(-0.1, eps)

    # The third vector predicted all labels, but only the first one was correct
    assert d_scores[2][0] == pytest.approx(0, eps)
    assert d_scores[2][1] == pytest.approx(0.25, eps)
    assert d_scores[2][2] == pytest.approx(0.25, eps)

    # The fourth vector predicted no labels but should have predicted the last one
    assert d_scores[3][0] == pytest.approx(0, eps)
    assert d_scores[3][1] == pytest.approx(0, eps)
    assert d_scores[3][2] == pytest.approx(-0.25, eps)

    loss = CategoricalCrossentropy(normalize=True).get_loss(guesses, labels)
    assert loss == pytest.approx(0.239375, eps)


@pytest.mark.parametrize(
    "guesses, labels", [(guesses1, labels1), (guesses1, labels1_full)]
)
def test_categorical_crossentropy_missing(guesses, labels):
    d_scores = CategoricalCrossentropy(normalize=True).get_grad(guesses, labels)
    assert d_scores.shape == guesses.shape


@pytest.mark.parametrize(
    "guesses, labels",
    [
        ([guesses1, guesses2], [labels1, labels2]),
        ([guesses1, guesses2], [labels1_full, labels2]),
    ],
)
def test_sequence_categorical_crossentropy(guesses, labels):
    d_scores = SequenceCategoricalCrossentropy(normalize=False).get_grad(
        guesses, labels
    )
    d_scores1 = d_scores[0]
    d_scores2 = d_scores[1]
    assert d_scores1.shape == guesses1.shape
    assert d_scores2.shape == guesses2.shape
    assert d_scores1[1][0] == pytest.approx(0.4, eps)
    assert d_scores1[1][1] == pytest.approx(-0.4, eps)
    # The normalization divides the difference (e.g. 0.4) by the number of seqs
    d_scores = SequenceCategoricalCrossentropy(normalize=True).get_grad(guesses, labels)
    d_scores1 = d_scores[0]
    d_scores2 = d_scores[1]

    assert d_scores1[1][0] == pytest.approx(0.2, eps)
    assert d_scores1[1][1] == pytest.approx(-0.2, eps)

    # The third vector predicted all labels, but only the first one was correct
    assert d_scores1[2][0] == pytest.approx(0, eps)
    assert d_scores1[2][1] == pytest.approx(0.5, eps)
    assert d_scores1[2][2] == pytest.approx(0.5, eps)

    # The fourth vector predicted no labels but should have predicted the last one
    assert d_scores1[3][0] == pytest.approx(0, eps)
    assert d_scores1[3][1] == pytest.approx(0, eps)
    assert d_scores1[3][2] == pytest.approx(-0.5, eps)

    # Test the second batch
    assert d_scores2[0][0] == pytest.approx(0.1, eps)
    assert d_scores2[0][1] == pytest.approx(-0.35, eps)

    loss = SequenceCategoricalCrossentropy(normalize=True).get_loss(guesses, labels)
    assert loss == pytest.approx(1.09, eps)


def test_L2():
    # L2 loss = 2²+4²=20 (or normalized: 1²+2²=5)
    vec1 = numpy.asarray([[1, 2], [8, 9]])
    vec2 = numpy.asarray([[1, 2], [10, 5]])
    d_vecs = L2Distance().get_grad(vec1, vec2)
    assert d_vecs.shape == vec1.shape
    numpy.testing.assert_allclose(
        d_vecs[0], numpy.zeros(d_vecs[0].shape), rtol=eps, atol=eps
    )

    loss_not_normalized = L2Distance(normalize=False).get_loss(vec1, vec2)
    assert loss_not_normalized == pytest.approx(20, eps)

    loss_normalized = L2Distance(normalize=True).get_loss(vec1, vec2)
    assert loss_normalized == pytest.approx(5, eps)


def test_cosine_orthogonal():
    # These are orthogonal, i.e. loss is 1
    vec1 = numpy.asarray([[0, 2], [0, 5]])
    vec2 = numpy.asarray([[8, 0], [7, 0]])

    d_vecs = CosineDistance(normalize=True).get_grad(vec1, vec2)
    assert d_vecs.shape == vec1.shape
    assert d_vecs[0][0] < 0
    assert d_vecs[0][1] > 0
    assert d_vecs[1][0] < 0
    assert d_vecs[1][1] > 0

    loss_not_normalized = CosineDistance(normalize=False).get_loss(vec1, vec2)
    assert loss_not_normalized == pytest.approx(2, eps)

    loss_normalized = CosineDistance(normalize=True).get_loss(vec1, vec2)
    assert loss_normalized == pytest.approx(1, eps)


def test_cosine_equal():
    # These 3 vectors are equal when measured with Cosine similarity, i.e. loss is 0
    vec1 = numpy.asarray([[1, 2], [8, 9], [3, 3]])
    vec2 = numpy.asarray([[1, 2], [80, 90], [300, 300]])

    d_vec1 = CosineDistance().get_grad(vec1, vec2)
    assert d_vec1.shape == vec1.shape
    numpy.testing.assert_allclose(d_vec1, numpy.zeros(d_vec1.shape), rtol=eps, atol=eps)

    loss_not_normalized = CosineDistance(normalize=False).get_loss(vec1, vec2)
    assert loss_not_normalized == pytest.approx(0, eps)

    loss_normalized = CosineDistance(normalize=True).get_loss(vec1, vec2)
    assert loss_normalized == pytest.approx(0, eps)


def test_cosine_unmatched():
    vec1 = numpy.asarray([[1, 2, 3]])
    vec2 = numpy.asarray([[1, 2]])
    with pytest.raises(ValueError):
        CosineDistance().get_grad(vec1, vec2)


@pytest.mark.parametrize(
    "name,kwargs,args",
    [
        ("CategoricalCrossentropy.v1", {}, (scores0, labels0)),
        ("SequenceCategoricalCrossentropy.v1", {}, ([scores0], [labels0])),
        ("L2Distance.v1", {}, (scores0, scores0)),
        (
            "CosineDistance.v1",
            {"normalize": True, "ignore_zeros": True},
            (scores0, scores0),
        ),
    ],
)
def test_loss_from_config(name, kwargs, args):
    """Test that losses are loaded and configured correctly from registry
    (as partials)."""
    cfg = {"test": {"@losses": name, **kwargs}}
    func = registry.make_from_config(cfg)["test"]
    loss = func.get_grad(*args)
    if isinstance(loss, (list, tuple)):
        loss = loss[0]
    assert loss.ndim == 2
    func.get_loss(*args)
    func(*args)
