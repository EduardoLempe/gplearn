"""Testing the Genetic Programming module's underlying datastructure
(gplearn.genetic._Program)."""

# Author: Trevor Stephens <trevorstephens.com>
#
# License: BSD 3 clause

import numpy as np
import pickle
import sys

from gplearn.genetic import _Program, SymbolicRegressor, SymbolicTransformer
from gplearn.genetic import weighted_pearson, weighted_spearman

from scipy.stats import pearsonr, spearmanr

from sklearn.externals.six.moves import StringIO
from sklearn.datasets import load_boston
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from gplearn.skutils.testing import assert_false, assert_true
from gplearn.skutils.testing import assert_greater
from gplearn.skutils.testing import assert_equal, assert_almost_equal
from gplearn.skutils.testing import assert_array_almost_equal
from gplearn.skutils.testing import assert_raises
from gplearn.skutils.validation import check_random_state

# load the boston dataset and randomly permute it
rng = check_random_state(0)
boston = load_boston()
perm = rng.permutation(boston.target.size)
boston.data = boston.data[perm]
boston.target = boston.target[perm]


def test_weighted_correlations():
    """Check weighted Pearson correlation coefficient matches scipy"""

    random_state = check_random_state(415)
    x1 = random_state.uniform(size=500)
    x2 = random_state.uniform(size=500)
    w1 = np.ones(500)
    w2 = random_state.uniform(size=500)

    # Pearson's correlation coefficient
    scipy_pearson = pearsonr(x1, x2)[0]
    # Check with constant weights (should be equal)
    gplearn_pearson = weighted_pearson(x1, x2, w1)
    assert_almost_equal(scipy_pearson, gplearn_pearson)
    # Check with irregular weights (should be different)
    gplearn_pearson = weighted_pearson(x1, x2, w2)
    assert_true(abs(scipy_pearson - gplearn_pearson) > 0.01)

    # Spearman's correlation coefficient
    scipy_spearman = spearmanr(x1, x2)[0]
    # Check with constant weights (should be equal)
    gplearn_spearman = weighted_spearman(x1, x2, w1)
    assert_almost_equal(scipy_spearman, gplearn_spearman)
    # Check with irregular weights (should be different)
    gplearn_spearman = weighted_pearson(x1, x2, w2)
    assert_true(abs(scipy_spearman - gplearn_spearman) > 0.01)


def test_program_init_method():
    """'full' should create longer and deeper programs than other methods"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2',
                               'sqrt1', 'log1', 'abs1', 'max2', 'min2'],
              'arities': {1: ['sqrt1', 'log1', 'abs1'],
                          2: ['add2', 'sub2', 'mul2', 'div2', 'max2', 'min2']},
              'init_depth': (2, 6),
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)
    programs = []
    for i in range(20):
        programs.append(_Program(init_method='full',
                                 random_state=random_state, **params))
    full_length = np.mean([gp.length_ for gp in programs])
    full_depth = np.mean([gp.depth_ for gp in programs])
    programs = []
    for i in range(20):
        programs.append(_Program(init_method='half and half',
                                 random_state=random_state, **params))
    hnh_length = np.mean([gp.length_ for gp in programs])
    hnh_depth = np.mean([gp.depth_ for gp in programs])
    programs = []
    for i in range(20):
        programs.append(_Program(init_method='grow',
                                 random_state=random_state, **params))
    grow_length = np.mean([gp.length_ for gp in programs])
    grow_depth = np.mean([gp.depth_ for gp in programs])

    assert_greater(full_length, hnh_length)
    assert_greater(hnh_length, grow_length)
    assert_greater(full_depth, hnh_depth)
    assert_greater(hnh_depth, grow_depth)


def test_program_init_depth():
    """'full' should create constant depth programs for single depth limit"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2',
                               'sqrt1', 'log1', 'abs1', 'max2', 'min2'],
              'arities': {1: ['sqrt1', 'log1', 'abs1'],
                          2: ['add2', 'sub2', 'mul2', 'div2', 'max2', 'min2']},
              'init_depth': (6, 6),
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)
    programs = []
    for i in range(20):
        programs.append(_Program(init_method='full',
                                 random_state=random_state, **params))
    full_depth = np.bincount([gp.depth_ for gp in programs])
    programs = []
    for i in range(20):
        programs.append(_Program(init_method='half and half',
                                 random_state=random_state, **params))
    hnh_depth = np.bincount([gp.depth_ for gp in programs])
    programs = []
    for i in range(20):
        programs.append(_Program(init_method='grow',
                                 random_state=random_state, **params))
    grow_depth = np.bincount([gp.depth_ for gp in programs])

    assert_true(full_depth[-1] == 20)
    assert_false(hnh_depth[-1] == 20)
    assert_false(grow_depth[-1] == 20)


def test_validate_program():
    """Check that valid programs are accepted & invalid ones raise error"""

    function_set = ['add2', 'sub2', 'mul2', 'div2',
                    'sqrt1', 'log1', 'abs1', 'max2', 'min2']
    arities = {1: ['sqrt1', 'log1', 'abs1'],
               2: ['add2', 'sub2', 'mul2', 'div2', 'max2', 'min2']}
    init_depth = (2, 6)
    init_method = 'half and half'
    n_features = 10
    const_range = (-1.0, 1.0)
    metric = 'mean absolute error'
    p_point_replace = 0.05
    parsimony_coefficient = 0.1

    random_state = check_random_state(415)
    test_gp = ['sub2', 'abs1', 'sqrt1', 'log1', 'log1', 'sqrt1', 7, 'abs1',
               'abs1', 'abs1', 'log1', 'sqrt1', 2]

    # This one should be fine
    _ = _Program(function_set, arities, init_depth, init_method, n_features,
                 const_range, metric, p_point_replace, parsimony_coefficient,
                 random_state, test_gp)

    # Now try a couple that shouldn't be
    assert_raises(ValueError, _Program, function_set, arities, init_depth,
                  init_method, n_features, const_range, metric,
                  p_point_replace, parsimony_coefficient, random_state,
                  test_gp[:-1])
    assert_raises(ValueError, _Program, function_set, arities, init_depth,
                  init_method, n_features, const_range, metric,
                  p_point_replace, parsimony_coefficient, random_state,
                  test_gp + [1])


def test_print_overloading():
    """Check that printing a program object results in 'pretty' output"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2'],
              'arities': {2: ['add2', 'sub2', 'mul2', 'div2']},
              'init_depth': (2, 6),
              'init_method': 'half and half',
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)

    test_gp = ['mul2', 'div2', 8, 1, 'sub2', 9, .5]

    gp = _Program(random_state=random_state, program=test_gp, **params)

    orig_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        print(gp)
        output = out.getvalue().strip()
    finally:
        sys.stdout = orig_stdout

    print(gp)
    lisp = "mul(div(X8, X1), sub(X9, 0.500))"
    assert_true(output == lisp)


def test_export_graphviz():
    """Check output of a simple program to Graphviz"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2'],
              'arities': {2: ['add2', 'sub2', 'mul2', 'div2']},
              'init_depth': (2, 6),
              'init_method': 'half and half',
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)

    # Test for a small program
    test_gp = ['mul2', 'div2', 8, 1, 'sub2', 9, .5]
    gp = _Program(random_state=random_state, program=test_gp, **params)
    output = gp.export_graphviz()
    tree = 'digraph program {\n' \
           'node [style=filled]0 [label="mul", fillcolor="#3499cd"] ;\n' \
           '1 [label="div", fillcolor="#3499cd"] ;\n' \
           '2 [label="X8", fillcolor="#f89939"] ;\n' \
           '3 [label="X1", fillcolor="#f89939"] ;\n' \
           '1 -> 3 ;\n1 -> 2 ;\n' \
           '4 [label="sub", fillcolor="#3499cd"] ;\n' \
           '5 [label="X9", fillcolor="#f89939"] ;\n' \
           '6 [label="0.500", fillcolor="#f89939"] ;\n' \
           '4 -> 6 ;\n4 -> 5 ;\n0 -> 4 ;\n0 -> 1 ;\n}'
    assert_true(output == tree)

    # Test a degenerative single-node program
    test_gp = [1]
    gp = _Program(random_state=random_state, program=test_gp, **params)
    output = gp.export_graphviz()
    tree = 'digraph program {\n' \
           'node [style=filled]0 [label="X1", fillcolor="#f89939"] ;\n}'
    assert_true(output == tree)


def test_execute():
    """Check executing the program works"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2'],
              'arities': {2: ['add2', 'sub2', 'mul2', 'div2']},
              'init_depth': (2, 6),
              'init_method': 'half and half',
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)

    # Test for a small program
    test_gp = ['mul2', 'div2', 8, 1, 'sub2', 9, .5]
    X = np.reshape(random_state.uniform(size=50), (5, 10))
    gp = _Program(random_state=random_state, program=test_gp, **params)
    result = gp.execute(X)
    expected = [-0.19656208, 0.78197782, -1.70123845, -0.60175969, -0.01082618]
    assert_array_almost_equal(result, expected)


def test_all_metrics():
    """Check all supported metrics work"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2'],
              'arities': {2: ['add2', 'sub2', 'mul2', 'div2']},
              'init_depth': (2, 6),
              'init_method': 'half and half',
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)

    # Test for a small program
    test_gp = ['mul2', 'div2', 8, 1, 'sub2', 9, .5]
    gp = _Program(random_state=random_state, program=test_gp, **params)
    X = np.reshape(random_state.uniform(size=50), (5, 10))
    y = random_state.uniform(size=5)
    sample_weight = np.ones(5)
    expected = [1.48719809776, 1.82389179833, 1.76013763179, 0.98663772258,
                -0.2928200724, -0.5]
    result = []
    for m in ['mean absolute error', 'mse', 'rmse', 'rmsle',
              'pearson', 'spearman']:
        gp.metric = m
        gp.raw_fitness_ = gp.raw_fitness(X, y, sample_weight)
        result.append(gp.fitness())
    assert_array_almost_equal(result, expected)
    # And check a fake one
    gp.metric = 'the larch'
    assert_raises(ValueError, gp.raw_fitness, X, y, sample_weight)


def test_get_subtree():
    """Check that get subtree does the same thing for self and new programs"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2'],
              'arities': {2: ['add2', 'sub2', 'mul2', 'div2']},
              'init_depth': (2, 6),
              'init_method': 'half and half',
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)

    # Test for a small program
    test_gp = ['mul2', 'div2', 8, 1, 'sub2', 9, .5]
    gp = _Program(random_state=random_state, program=test_gp, **params)

    self_test = gp.get_subtree(check_random_state(0))
    external_test = gp.get_subtree(check_random_state(0), test_gp)

    assert_equal(self_test, external_test)


def test_genetic_operations():
    """Check all genetic operations are stable and don't change programs"""

    params = {'function_set': ['add2', 'sub2', 'mul2', 'div2'],
              'arities': {2: ['add2', 'sub2', 'mul2', 'div2']},
              'init_depth': (2, 6),
              'init_method': 'half and half',
              'n_features': 10,
              'const_range': (-1.0, 1.0),
              'metric': 'mean absolute error',
              'p_point_replace': 0.05,
              'parsimony_coefficient': 0.1}
    random_state = check_random_state(415)

    # Test for a small program
    test_gp = ['mul2', 'div2', 8, 1, 'sub2', 9, .5]
    donor = ['add2', 0.1, 'sub2', 2, 7]

    gp = _Program(random_state=random_state, program=test_gp, **params)

    assert_equal(gp.reproduce(),
                 ['mul2', 'div2', 8, 1, 'sub2', 9, 0.5])
    assert_equal(gp.program, test_gp)
    assert_equal(gp.crossover(donor, random_state)[0],
                 ['sub2', 2, 7])
    assert_equal(gp.program, test_gp)
    assert_equal(gp.subtree_mutation(random_state)[0],
                 ['mul2', 'div2', 8, 1, 'sub2', 'sub2', 3, 5, 'add2', 6, 3])
    assert_equal(gp.program, test_gp)
    assert_equal(gp.hoist_mutation(random_state)[0],
                 ['div2', 8, 1])
    assert_equal(gp.program, test_gp)
    assert_equal(gp.point_mutation(random_state)[0],
                 ['mul2', 'div2', 8, 1, 'sub2', 9, 0.5])
    assert_equal(gp.program, test_gp)


def test_program_input_validation():
    """Check that guarded input validation raises errors"""

    for Symbolic in (SymbolicRegressor, SymbolicTransformer):
        # Check too much proba
        est = Symbolic(p_point_mutation=.5)
        assert_raises(ValueError, est.fit, boston.data, boston.target)

        # Check invalid init_method
        est = Symbolic(init_method='ni')
        assert_raises(ValueError, est.fit, boston.data, boston.target)

        # Check invalid const_ranges
        est = Symbolic(const_range=2)
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(const_range=[2, 2])
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(const_range=(2, 2, 2))
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(const_range='ni')
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        # And check acceptable, but strange, representations of init_depth
        est = Symbolic(const_range=(2, 2))
        est.fit(boston.data, boston.target)
        est = Symbolic(const_range=(4, 2))
        est.fit(boston.data, boston.target)

        # Check invalid init_depth
        est = Symbolic(init_depth=2)
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(init_depth=2)
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(init_depth=[2, 2])
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(init_depth=(2, 2, 2))
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(init_depth='ni')
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        est = Symbolic(init_depth=(4, 2))
        assert_raises(ValueError, est.fit, boston.data, boston.target)
        # And check acceptable, but strange, representations of init_depth
        est = Symbolic(init_depth=(2, 2))
        est.fit(boston.data, boston.target)

    # Check hall_of_fame and n_components for transformer
    est = SymbolicTransformer(hall_of_fame=1000)
    assert_raises(ValueError, est.fit, boston.data, boston.target)
    est = SymbolicTransformer(n_components=1000)
    assert_raises(ValueError, est.fit, boston.data, boston.target)

    # Check regressor metrics
    for m in ['mean absolute error', 'mse', 'rmse', 'rmsle']:
        est = SymbolicRegressor(generations=2, metric=m)
        est.fit(boston.data, boston.target)
    # And check the transformer metrics as well as a fake one
    for m in ['pearson', 'spearman', 'the larch']:
        est = SymbolicRegressor(generations=2, metric=m)
        assert_raises(ValueError, est.fit, boston.data, boston.target)
    # Check transformer metrics
    for m in ['pearson', 'spearman']:
        est = SymbolicTransformer(generations=2, metric=m)
        est.fit(boston.data, boston.target)
    # And check the regressor metrics as well as a fake one
    for m in ['mean absolute error', 'mse', 'rmse', 'rmsle', 'the larch']:
        est = SymbolicTransformer(generations=2, metric=m)
        assert_raises(ValueError, est.fit, boston.data, boston.target)


def test_sample_weight():
    """Check sample_weight param works"""

    # Check constant sample_weight has no effect
    sample_weight = np.ones(boston.target.shape[0])
    est1 = SymbolicRegressor(generations=2, random_state=0)
    est1.fit(boston.data, boston.target)
    est2 = SymbolicRegressor(generations=2, random_state=0)
    est2.fit(boston.data, boston.target, sample_weight=sample_weight)
    # And again with a scaled sample_weight
    est3 = SymbolicRegressor(generations=2, random_state=0)
    est3.fit(boston.data, boston.target, sample_weight=sample_weight * 1.1)

    assert_almost_equal(est1.fitness_, est2.fitness_)
    assert_almost_equal(est1.fitness_, est3.fitness_)

    # And again for the transformer
    sample_weight = np.ones(boston.target.shape[0])
    est1 = SymbolicTransformer(generations=2, random_state=0)
    est1 = est1.fit_transform(boston.data, boston.target)
    est2 = SymbolicTransformer(generations=2, random_state=0)
    est2 = est2.fit_transform(boston.data, boston.target,
                              sample_weight=sample_weight)
    # And again with a scaled sample_weight
    est3 = SymbolicTransformer(generations=2, random_state=0)
    est3 = est3.fit_transform(boston.data, boston.target,
                              sample_weight=sample_weight * 1.1)

    assert_array_almost_equal(est1, est2)
    assert_array_almost_equal(est1, est3)


def test_trigonometric():
    """Check that using trig functions work and that results differ"""

    est1 = SymbolicRegressor(random_state=0)
    est1.fit(boston.data[:400, :], boston.target[:400])
    est1 = mean_absolute_error(est1.predict(boston.data[400:, :]),
                               boston.target[400:])

    est2 = SymbolicRegressor(trigonometric=True, random_state=0)
    est2.fit(boston.data[:400, :], boston.target[:400])
    est2 = mean_absolute_error(est2.predict(boston.data[400:, :]),
                               boston.target[400:])

    assert_true(abs(est1 - est2) > 0.01)


def test_bootstrap_and_subsample():
    """Check that bootstrap and subsample work and that results differ"""

    est1 = SymbolicRegressor(bootstrap=False, max_samples=1.0, random_state=0)
    est1.fit(boston.data[:400, :], boston.target[:400])
    est1 = mean_absolute_error(est1.predict(boston.data[400:, :]),
                               boston.target[400:])

    est2 = SymbolicRegressor(bootstrap=True, max_samples=1.0, random_state=0)
    est2.fit(boston.data[:400, :], boston.target[:400])
    est2 = mean_absolute_error(est2.predict(boston.data[400:, :]),
                               boston.target[400:])

    est3 = SymbolicRegressor(bootstrap=False, max_samples=0.7, random_state=0)
    est3.fit(boston.data[:400, :], boston.target[:400])
    est3 = mean_absolute_error(est3.predict(boston.data[400:, :]),
                               boston.target[400:])

    est4 = SymbolicRegressor(bootstrap=True, max_samples=0.7, random_state=0)
    est4.fit(boston.data[:400, :], boston.target[:400])
    est4 = mean_absolute_error(est4.predict(boston.data[400:, :]),
                               boston.target[400:])

    for e1 in [est1, est2, est3, est4]:
        for e2 in [est1, est2, est3, est4]:
            if e1 is not e2:
                assert_true(abs(e1 - e2) > 0.01)


def test_parsimony_coefficient():
    """Check that parsimony coefficients work and that results differ"""

    est1 = SymbolicRegressor(parsimony_coefficient=0.001, random_state=0)
    est1.fit(boston.data[:400, :], boston.target[:400])
    est1 = mean_absolute_error(est1.predict(boston.data[400:, :]),
                               boston.target[400:])

    est2 = SymbolicRegressor(parsimony_coefficient=0.1, random_state=0)
    est2.fit(boston.data[:400, :], boston.target[:400])
    est2 = mean_absolute_error(est2.predict(boston.data[400:, :]),
                               boston.target[400:])

    est3 = SymbolicRegressor(parsimony_coefficient='auto', random_state=0)
    est3.fit(boston.data[:400, :], boston.target[:400])
    est3 = mean_absolute_error(est3.predict(boston.data[400:, :]),
                               boston.target[400:])

    assert_true(abs(est1 - est2) > 0.01)
    assert_true(abs(est1 - est3) > 0.01)
    assert_true(abs(est2 - est3) > 0.01)


def test_verbose_output():
    """Check verbose=1 does not cause error"""

    old_stdout = sys.stdout
    sys.stdout = StringIO()
    est = SymbolicRegressor(random_state=0, verbose=1)
    est.fit(boston.data, boston.target)
    verbose_output = sys.stdout
    sys.stdout = old_stdout

    # check output
    verbose_output.seek(0)
    header1 = verbose_output.readline().rstrip()
    true_header = '%4s|%-25s|%-59s|' % (' ', 'Population Average'.center(25),
                                        'Best Individual'.center(59))
    assert_equal(true_header, header1)

    header2 = verbose_output.readline().rstrip()
    true_header = '-' * 4 + ' ' + '-' * 25 + ' ' + '-' * 59 + ' ' + '-' * 10
    assert_equal(true_header, header2)

    header3 = verbose_output.readline().rstrip()
    header_fields = ('Gen', 'Length', 'Fitness', 'Length', 'Fitness',
                     'Raw Fitness', 'OOB Fitness', 'Time Left')
    true_header = '%4s %8s %16s %8s %16s %16s %16s %10s' % header_fields
    assert_equal(true_header, header3)

    n_lines = sum(1 for l in verbose_output.readlines())
    assert_equal(10, n_lines)


def test_verbose_with_oob():
    """Check oob scoring for bootstrap or subsample does not cause error"""

    # Check subsample
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    est = SymbolicRegressor(max_samples=0.9, random_state=0, verbose=1)
    est.fit(boston.data, boston.target)
    verbose_output = sys.stdout
    sys.stdout = old_stdout

    # check output
    verbose_output.seek(0)
    header1 = verbose_output.readline().rstrip()
    header2 = verbose_output.readline().rstrip()
    header3 = verbose_output.readline().rstrip()

    n_lines = sum(1 for l in verbose_output.readlines())
    assert_equal(10, n_lines)

    # Check bootstrap
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    est = SymbolicRegressor(bootstrap=True, random_state=0, verbose=1)
    est.fit(boston.data, boston.target,
            sample_weight=np.ones(boston.target.shape) * 1.1)
    verbose_output = sys.stdout
    sys.stdout = old_stdout

    # check output
    verbose_output.seek(0)
    header1 = verbose_output.readline().rstrip()
    header2 = verbose_output.readline().rstrip()
    header3 = verbose_output.readline().rstrip()

    n_lines = sum(1 for l in verbose_output.readlines())
    assert_equal(10, n_lines)


def test_more_verbose_output():
    """Check verbose=2 does not cause error"""

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    est = SymbolicRegressor(random_state=0, verbose=2)
    est.fit(boston.data, boston.target)
    verbose_output = sys.stdout
    joblib_output = sys.stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    # check output
    verbose_output.seek(0)
    header1 = verbose_output.readline().rstrip()
    header2 = verbose_output.readline().rstrip()
    header3 = verbose_output.readline().rstrip()

    n_lines = sum(1 for l in verbose_output.readlines())
    assert_equal(10, n_lines)

    joblib_output.seek(0)
    n_lines = sum(1 for l in joblib_output.readlines())
    assert_equal(20, n_lines)


def test_parallel_train():
    """Check predictions are the same for different n_jobs"""

    # Check the regressor
    ests = [
        SymbolicRegressor(population_size=100, generations=4, n_jobs=n_jobs,
                          random_state=0).fit(boston.data[:100, :],
                                              boston.target[:100])
        for n_jobs in [1, 2, 3, 8, 16]
    ]

    preds = [e.predict(boston.data[500:, :]) for e in ests]
    for pred1, pred2 in zip(preds, preds[1:]):
        assert_array_almost_equal(pred1, pred2)
    lengths = np.array([[gp.length_ for gp in e._programs[-1]] for e in ests])
    for len1, len2 in zip(lengths, lengths[1:]):
        assert_array_almost_equal(len1, len2)

    # Check the transformer
    ests = [
        SymbolicTransformer(population_size=100, hall_of_fame=50,
                            generations=4, n_jobs=n_jobs,
                            random_state=0).fit(boston.data[:100, :],
                                                boston.target[:100])
        for n_jobs in [1, 2, 3, 8, 16]
    ]

    preds = [e.transform(boston.data[500:, :]) for e in ests]
    for pred1, pred2 in zip(preds, preds[1:]):
        assert_array_almost_equal(pred1, pred2)
    lengths = np.array([[gp.length_ for gp in e._programs[-1]] for e in ests])
    for len1, len2 in zip(lengths, lengths[1:]):
        assert_array_almost_equal(len1, len2)


def test_pickle():
    """Check pickability"""

    # Check the regressor
    est = SymbolicRegressor(generations=2, random_state=0)
    est.fit(boston.data[:100, :], boston.target[:100])
    score = est.score(boston.data[500:, :], boston.target[500:])
    pickle_object = pickle.dumps(est)

    est2 = pickle.loads(pickle_object)
    assert_equal(type(est2), est.__class__)
    score2 = est2.score(boston.data[500:, :], boston.target[500:])
    assert_equal(score, score2)

    # Check the transformer
    est = SymbolicTransformer(generations=2, random_state=0)
    est.fit(boston.data[:100, :], boston.target[:100])
    X_new = est.transform(boston.data[500:, :])
    pickle_object = pickle.dumps(est)

    est2 = pickle.loads(pickle_object)
    assert_equal(type(est2), est.__class__)
    X_new2 = est2.transform(boston.data[500:, :])
    assert_array_almost_equal(X_new, X_new2)


def test_memory_layout():
    """Check that it works no matter the memory layout"""

    for Symbolic in [SymbolicTransformer, SymbolicRegressor]:
        for dtype in [np.float64, np.float32]:
            est = Symbolic(generations=2, random_state=0)

            # Nothing
            X = np.asarray(boston.data, dtype=dtype)
            y = boston.target
            est.fit(X, y)

            # C-order
            X = np.asarray(boston.data, order="C", dtype=dtype)
            y = boston.target
            est.fit(X, y)

            # F-order
            X = np.asarray(boston.data, order="F", dtype=dtype)
            y = boston.target
            est.fit(X, y)

            # Contiguous
            X = np.ascontiguousarray(boston.data, dtype=dtype)
            y = boston.target
            est.fit(X, y)

            # Strided
            X = np.asarray(boston.data[::3], dtype=dtype)
            y = boston.target[::3]
            est.fit(X, y)


def test_input_shape():
    """Check changed dimensions cause failure"""

    random_state = check_random_state(415)
    X = np.reshape(random_state.uniform(size=50), (5, 10))
    y = random_state.uniform(size=5)
    X2 = np.reshape(random_state.uniform(size=45), (5, 9))

    # Check the regressor
    est = SymbolicRegressor(generations=2, random_state=0)
    est.fit(X, y)
    assert_raises(ValueError, est.predict, X2)

    # Check the transformer
    est = SymbolicTransformer(generations=2, random_state=0)
    est.fit(X, y)
    assert_raises(ValueError, est.transform, X2)


def test_gridsearch():
    """Check that SymbolicRegressor can be grid-searched"""

    # Grid search parsimony_coefficient
    parameters = {'parsimony_coefficient': [0.001, 0.1, 'auto']}
    clf = SymbolicRegressor(population_size=50, generations=5,
                            tournament_size=5, random_state=0)
    grid = GridSearchCV(clf, parameters, scoring='mean_absolute_error')
    grid.fit(boston.data, boston.target)
    expected = {'parsimony_coefficient': 0.001}
    assert_equal(grid.best_params_, expected)


def test_pipeline():
    """Check that SymbolicRegressor/Transformer can work in a pipeline"""

    # Check the regressor
    est = make_pipeline(StandardScaler(),
                        SymbolicRegressor(population_size=50,
                                          generations=5,
                                          tournament_size=5,
                                          random_state=0))
    est.fit(boston.data, boston.target)
    assert_almost_equal(est.score(boston.data, boston.target), -4.84921978246)

    # Check the transformer
    est = make_pipeline(SymbolicTransformer(population_size=50,
                                            hall_of_fame=20,
                                            generations=5,
                                            tournament_size=5,
                                            random_state=0),
                        DecisionTreeRegressor())
    est.fit(boston.data, boston.target)
    assert_almost_equal(est.score(boston.data, boston.target), 1.0)


if __name__ == "__main__":
    import nose
    nose.runmodule()
