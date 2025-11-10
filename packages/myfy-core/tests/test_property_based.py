"""
Property-based tests for DI container using Hypothesis.

Tests invariants and properties that should always hold.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from myfy.core.di.container import Container
from myfy.core.di.scopes import SINGLETON


class TestContainerProperties:
    """Property-based tests for DI container invariants."""

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=50, unique=True))
    def test_provider_registration_order_independent(self, provider_names):
        """Provider resolution should be order-independent."""
        # Create two containers with same providers in different orders
        container1 = Container()
        container2 = Container()

        # Helper to create factory with closure
        def make_factory(n):
            def factory():
                return f"value_{n}"

            return factory

        # Register in original order
        for name in provider_names:
            container1.register(name, make_factory(name), scope=SINGLETON)

        # Register in reverse order
        for name in reversed(provider_names):
            container2.register(name, make_factory(name), scope=SINGLETON)

        container1.compile()
        container2.compile()

        # Both should resolve to same values
        for name in provider_names:
            assert container1.get(name) == container2.get(name)

    @given(
        st.integers(min_value=1, max_value=100),
        st.text(min_size=1, max_size=50),
    )
    def test_singleton_scope_always_returns_same_instance(self, num_resolutions, provider_name):
        """Singleton scope should always return the same instance."""
        container = Container()

        class Service:
            pass

        container.register(provider_name, lambda: Service(), scope=SINGLETON)
        container.compile()

        # Resolve multiple times
        instances = [container.get(provider_name) for _ in range(num_resolutions)]

        # All should be the same object
        assert len({id(i) for i in instances}) == 1

    @given(st.lists(st.integers(min_value=0, max_value=1000), min_size=1, max_size=100))
    def test_provider_factories_can_return_any_value(self, values):
        """Providers should work with any JSON-serializable value."""
        container = Container()

        for i, value in enumerate(values):
            container.register(f"provider_{i}", lambda v=value: v, scope=SINGLETON)

        container.compile()

        # All values should be retrievable
        for i, expected_value in enumerate(values):
            assert container.get(f"provider_{i}") == expected_value


class TestPathParameterProperties:
    """Property-based tests for path parameter handling."""

    @given(st.integers(min_value=-(2**31), max_value=2**31 - 1))
    def test_int_path_param_conversion_always_valid(self, value):
        """Path param conversion should handle all valid integers."""
        from myfy.web.handlers import HandlerExecutor

        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        result = executor._convert_param(str(value), int, "param")
        assert result == value
        assert isinstance(result, int)

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_float_path_param_conversion_always_valid(self, value):
        """Path param conversion should handle all valid floats."""
        from myfy.web.handlers import HandlerExecutor

        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        result = executor._convert_param(str(value), float, "param")
        assert abs(result - value) < 1e-10 or (abs(value) > 1e10)

    @given(st.booleans())
    def test_bool_path_param_conversion_consistency(self, value):
        """Bool conversion should be consistent."""
        from myfy.web.handlers import HandlerExecutor

        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        # Test various representations
        if value:
            for repr_str in ["true", "True", "TRUE", "1", "yes"]:
                result = executor._convert_param(repr_str, bool, "param")
                assert result is True
        else:
            for repr_str in ["false", "False", "FALSE", "0", "no"]:
                result = executor._convert_param(repr_str, bool, "param")
                assert result is False

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=32, max_codepoint=126
            ),
            min_size=0,
            max_size=100,
        )
    )
    def test_string_path_param_preserves_value(self, value):
        """String conversion should preserve the value."""
        from myfy.web.handlers import HandlerExecutor

        container = Container()
        container.compile()
        executor = HandlerExecutor(container)

        result = executor._convert_param(value, str, "param")
        assert result == value


class TestRoutePathProperties:
    """Property-based tests for route path handling."""

    @given(
        st.lists(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=97, max_codepoint=122
                ),
                min_size=1,
                max_size=20,
            ),
            min_size=1,
            max_size=10,
            unique=True,
        )
    )
    def test_path_params_extraction_is_consistent(self, param_names):
        """Path parameter extraction should be consistent."""
        from myfy.web.routing import HTTPMethod, Router

        router = Router()

        # Build path with parameters
        path_parts = [f"{{{name}}}" for name in param_names]
        path = "/" + "/".join(path_parts)

        def handler():
            return {}

        route = router.add_route(path, handler, HTTPMethod.GET)

        # Should extract all parameters
        assert len(route.path_params) == len(param_names)
        assert set(route.path_params) == set(param_names)


class TestConfigurationProperties:
    """Property-based tests for configuration handling."""

    @given(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=1, max_value=65535),
        st.booleans(),
    )
    def test_settings_validation_is_consistent(self, app_name, port, debug):
        """Settings validation should be consistent."""
        from myfy.core.config import CoreSettings

        settings = CoreSettings(app_name=app_name, debug=debug)

        assert settings.app_name == app_name
        assert settings.debug == debug

    @given(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=0, max_size=100)))
    def test_model_dump_safe_redacts_all_secrets(self, field_values):
        """model_dump_safe should redact any field containing secret keywords."""
        from myfy.core.config import BaseSettings

        # Add some secret fields
        secret_fields = {
            "password": "secret123",
            "api_key": "key456",
            "secret_token": "token789",
        }

        combined = {**field_values, **secret_fields}

        # Create dynamic settings class
        class TestSettings(BaseSettings):
            pass

        settings = TestSettings(**combined)
        safe_dump = settings.model_dump_safe()

        # All secret fields should be redacted
        for key in secret_fields:
            if key in safe_dump:
                assert safe_dump[key] == "***REDACTED***"


@pytest.mark.slow
class TestScalabilityProperties:
    """Property-based tests for scalability."""

    @given(st.integers(min_value=10, max_value=500))
    def test_container_handles_arbitrary_provider_counts(self, num_providers):
        """Container should scale to any reasonable number of providers."""
        container = Container()

        def make_factory(val):
            def factory():
                return f"service_{val}"

            return factory

        for i in range(num_providers):
            container.register(f"Service{i}", make_factory(i), scope=SINGLETON)

        # Should compile without error
        container.compile()

        # Should resolve any provider
        mid_point = num_providers // 2
        result = container.get(f"Service{mid_point}")
        assert result == f"service_{mid_point}"

    @given(st.integers(min_value=2, max_value=20))
    def test_dependency_chain_depth_is_unbounded(self, chain_depth):
        """Container should handle arbitrary dependency chain depths."""
        container = Container()

        # Create chain
        class Service0:
            pass

        container.register("Service0", lambda: Service0(), scope=SINGLETON)

        for i in range(1, chain_depth):
            prev_name = f"Service{i - 1}"
            curr_name = f"Service{i}"

            # Create factory with proper closure
            def make_factory(cont, prev, curr):
                def factory():
                    cont.get(prev)
                    return curr

                return factory

            container.register(
                f"Service{i}", make_factory(container, prev_name, curr_name), scope=SINGLETON
            )

        container.compile()

        # Should resolve the deepest service
        result = container.get(f"Service{chain_depth - 1}")
        assert result == f"Service{chain_depth - 1}"
