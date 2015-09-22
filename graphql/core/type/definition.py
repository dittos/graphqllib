import collections
import copy
import re
from ..language import ast


def is_input_type(type):
    named_type = get_named_type(type)
    return isinstance(named_type, (
        GraphQLScalarType,
        GraphQLEnumType,
        GraphQLInputObjectType,
    ))


def is_output_type(type):
    named_type = get_named_type(type)
    return isinstance(named_type, (
        GraphQLScalarType,
        GraphQLObjectType,
        GraphQLInterfaceType,
        GraphQLUnionType,
        GraphQLEnumType,
    ))


def is_composite_type(type):
    named_type = get_named_type(type)
    return isinstance(named_type, (
        GraphQLObjectType,
        GraphQLInterfaceType,
        GraphQLUnionType,
    ))


def is_leaf_type(type):
    named_type = get_named_type(type)
    return isinstance(named_type, (
        GraphQLScalarType,
        GraphQLEnumType,
    ))


def get_named_type(type):
    unmodified_type = type
    while isinstance(unmodified_type, (GraphQLList, GraphQLNonNull)):
        unmodified_type = unmodified_type.of_type
    return unmodified_type


def get_nullable_type(type):
    if isinstance(type, GraphQLNonNull):
        return type.of_type
    return type


class GraphQLType(object):
    def __str__(self):
        return self.name

    def is_same_type(self, other):
        return self.__class__ is other.__class__ and self.name == other.name


NAME_PATTERN = re.compile(r'^[_a-zA-Z][_a-zA-Z0-9]*$')


def assert_valid_name(name):
    assert NAME_PATTERN.match(name), \
        'Names must match /^[_a-zA-Z][_a-zA-Z0-9]*$/ but "{}" does not.'.format(name)


class GraphQLScalarType(GraphQLType):
    """Scalar Type Definition

    The leaf values of any request and input values to arguments are
    Scalars (or Enums) and are defined with a name and a series of coercion
    functions used to ensure validity.

    Example:

        def coerce_odd(value):
            if value % 2 == 1:
                return value
            return None

        OddType = GraphQLScalarType(name='Odd', serialize=coerce_odd)
    """
    def __init__(self, name, description=None, serialize=None, parse_value=None, parse_literal=None):
        assert name, 'Type must be named.'
        assert_valid_name(name)
        self.name = name
        self.description = description
        assert callable(serialize), (
            '{} must provide "serialize" function. If this custom Scalar is '
            'also used as an input type, ensure "parse_value" and "parse_literal" '
            'functions are also provided.'
        ).format(self)
        if parse_value or parse_literal:
            assert callable(parse_value) and callable(parse_literal), \
                '{} must provide both "parse_value" and "parse_literal" functions.'.format(self)
        self._serialize = serialize
        self._parse_value = parse_value
        self._parse_literal = parse_literal

    def serialize(self, value):
        return self._serialize(value)

    def parse_value(self, value):
        if self._parse_value:
            return self._parse_value(value)
        return None

    def parse_literal(self, value_ast):
        if self._parse_literal:
            return self._parse_literal(value_ast)
        return None

    def __str__(self):
        return self.name


class GraphQLObjectType(GraphQLType):
    """Object Type Definition

    Almost all of the GraphQL types you define will be object types.
    Object types have a name, but most importantly describe their fields.

    Example:

        AddressType = GraphQLObjectType('Address', {
            'street': GraphQLField(GraphQLString),
            'number': GraphQLField(GraphQLInt),
            'formatted': GraphQLField(GraphQLString,
                resolver=lambda obj, args, info: obj.number + ' ' + obj.street),
        })

    When two types need to refer to each other, or a type needs to refer to
    itself in a field, you can use a static method to supply the fields
    lazily.

    Example:

        PersonType = GraphQLObjectType('Person', lambda: {
            'name': GraphQLField(GraphQLString),
            'bestFriend': GraphQLField(PersonType)
        })
    """
    def __init__(self, name, fields, interfaces=None, is_type_of=None, description=None):
        assert name, 'Type must be named.'
        assert_valid_name(name)
        self.name = name
        self.description = description
        if is_type_of:
            assert callable(is_type_of), '{} must provide "is_type_of" as a function.'.format(self)
        self.is_type_of = is_type_of
        self._fields = fields
        self._provided_interfaces = interfaces
        self._field_map = None
        self._interfaces = None
        add_impl_to_interfaces(self)

    def get_fields(self):
        if self._field_map is None:
            self._field_map = define_field_map(self, self._fields)
        return self._field_map

    def get_interfaces(self):
        if self._interfaces is None:
            self._interfaces = define_interfaces(self, self._provided_interfaces)
        return self._interfaces


def define_interfaces(type, interfaces):
    if callable(interfaces):
        interfaces = interfaces()
    if interfaces is None:
        return []
    assert isinstance(interfaces, (list, tuple)), \
        '{} interfaces must be an list/tuple or a function which returns an list/tuple.'.format(type)
    for iface in interfaces:
        assert isinstance(iface, GraphQLInterfaceType), \
            '{} may only implement Interface types, it cannot implement: {}.'.format(type, iface)
        if not callable(iface.type_resolver):
            assert callable(type.is_type_of), (
                'Interface Type {} does not provide a "resolve_type" function '
                'and implementing Type {} does not provide a "is_type_of" '
                'function. There is no way to resolve this implementing type '
                'during execution.'
            ).format(iface, type)
    return interfaces


def define_field_map(type, fields):
    if callable(fields):
        fields = fields()
    assert isinstance(fields, collections.Mapping), (
        '{} fields must be an mapping (dict) with field names as keys or a '
        'function which returns such an mapping.'
    ).format(type)
    assert len(fields) > 0, (
        '{} fields must be an mapping (dict) with field names as keys or a '
        'function which returns such an mapping.'
    ).format(type)

    field_map = {}
    for field_name, field in fields.items():
        assert_valid_name(field_name)
        field = copy.copy(field)
        field.name = field_name
        assert is_output_type(field.type), \
            '{}.{} field type must be Output Type but got: {}'.format(type, field_name, field.type)
        if not field.args:
            field.args = []
        else:
            assert isinstance(field.args, collections.Mapping), \
                '{}.{} args must be an mapping (dict) with argument names as keys.'.format(type, field_name)
            args = []
            for arg_name, arg in field.args.items():
                assert_valid_name(arg_name)
                assert is_input_type(arg.type), (
                    '{}.{}({}:) argument type must be Input Type but got: {}.'
                ).format(type, field_name, arg_name, arg.type)
                arg = copy.copy(arg)
                arg.name = arg_name
                args.append(arg)
            field.args = args
        field_map[field_name] = field
    return field_map


def add_impl_to_interfaces(impl):
    for type in impl.get_interfaces():
        type._impls.append(impl)


class GraphQLField(object):
    def __init__(self, type, args=None, resolver=None,
                 deprecation_reason=None, description=None):
        self.type = type
        self.args = args
        self.resolver = resolver
        self.deprecation_reason = deprecation_reason
        self.description = description


class GraphQLArgument(object):
    def __init__(self, type, default_value=None, description=None):
        self.type = type
        self.default_value = default_value
        self.description = description


class GraphQLInterfaceType(GraphQLType):
    """Interface Type Definition

    When a field can return one of a heterogeneous set of types, a Interface type is used to describe what types are possible,
    what fields are in common across all types, as well as a function to determine which type is actually used when the field is resolved.

    Example:

        EntityType = GraphQLInterfaceType(
            name='Entity',
            fields={
                'name': GraphQLField(GraphQLString),
            })
    """

    def __init__(self, name, fields=None, resolve_type=None, description=None):
        assert name, 'Type must be named.'
        assert_valid_name(name)
        self.name = name
        self.description = description
        if resolve_type:
            assert callable(resolve_type), '{} must provide "resolve_type" as a function.'.format(self)
        self.type_resolver = resolve_type
        self._fields = fields

        self._impls = []
        self._field_map = None
        self._possible_type_names = None

    def get_fields(self):
        if self._field_map is None:
            self._field_map = define_field_map(self, self._fields)
        return self._field_map

    def get_possible_types(self):
        return self._impls

    def is_possible_type(self, type):
        if self._possible_type_names is None:
            self._possible_type_names = set(
                t.name for t in self.get_possible_types()
            )
        return type.name in self._possible_type_names

    def resolve_type(self, value):
        if self.type_resolver:
            return self.type_resolver(value)
        return get_type_of(value, self)


def get_type_of(value, abstract_type):
    possible_types = abstract_type.get_possible_types()
    for type in possible_types:
        if callable(type.is_type_of) and type.is_type_of(value):
            return type


class GraphQLUnionType(GraphQLType):
    """Union Type Definition

    When a field can return one of a heterogeneous set of types, a Union type is used to describe what types are possible
    as well as providing a function to determine which type is actually used when the field is resolved.

    Example:

        class PetType(GraphQLUnionType):
            name = 'Pet'
            types = [DogType, CatType]

            def resolve_type(self, value):
                if isinstance(value, Dog):
                    return DogType()
                if isinstance(value, Cat):
                    return CatType()
    """
    def __init__(self, name, types=None, resolve_type=None, description=None):
        assert name, 'Type must be named.'
        assert_valid_name(name)
        self.name = name
        self.description = description
        if resolve_type:
            assert callable(resolve_type), '{} must provide "resolve_type" as a function.'.format(self)
        self._resolve_type = resolve_type
        assert types, \
            'Must provide types for Union {}.'.format(name)
        for type in types:
            assert isinstance(type, GraphQLObjectType), \
                '{} may only contain Object types, it cannot contain: {}'.format(self, type)
            if not callable(self._resolve_type):
                assert callable(type.is_type_of), (
                    'Union Type {} does not provide a "resolve_type" function '
                    'and possible Type {} does not provide a "is_type_of" '
                    'function. There is no way to resolve this possible type '
                    'during execution.'
                ).format(self, type)
        self._types = types
        self._possible_type_names = None

    def get_possible_types(self):
        return self._types

    def is_possible_type(self, type):
        if self._possible_type_names is None:
            self._possible_type_names = set(
                t.name for t in self.get_possible_types()
            )
        return type.name in self._possible_type_names

    def resolve_type(self, value):
        if self._resolve_type:
            return self._resolve_type(value)
        return get_type_of(value, self)


class GraphQLEnumType(GraphQLType):
    """Enum Type Definition

    Some leaf values of requests and input values are Enums. GraphQL serializes Enum values as strings,
    however internally Enums can be represented by any kind of type, often integers.

    Example:

        RGBType = GraphQLEnumType('RGB', {
            'RED': 0,
            'GREEN': 1,
            'BLUE': 2,
        })

    Note: If a value is not provided in a definition, the name of the enum value will be used as it's internal value.
    """
    def __init__(self, name, values, description=None):
        self.name = name
        assert_valid_name(name)
        self.description = description
        self._values = define_enum_values(self, values)
        self._value_lookup = None
        self._name_lookup = None

    def get_values(self):
        return self._values

    def serialize(self, value):
        if isinstance(value, collections.Hashable):
            enum_value = self._get_value_lookup().get(value)
            if enum_value:
                return enum_value.name
        return None

    def parse_value(self, value):
        if isinstance(value, collections.Hashable):
            enum_value = self._get_value_lookup().get(value)
            if enum_value:
                return enum_value.name
        return None

    def parse_literal(self, value_ast):
        if isinstance(value_ast, ast.EnumValue):
            enum_value = self._get_name_lookup().get(value_ast.value)
            if enum_value:
                return enum_value.value

    def _get_value_lookup(self):
        if self._value_lookup is None:
            lookup = {}
            for value in self.get_values():
                lookup[value.value] = value
            self._value_lookup = lookup
        return self._value_lookup

    def _get_name_lookup(self):
        if self._name_lookup is None:
            lookup = {}
            for value in self.get_values():
                lookup[value.name] = value
            self._name_lookup = lookup
        return self._name_lookup


def define_enum_values(type, value_map):
    assert isinstance(value_map, collections.Mapping), \
        '{} values must be an mapping (dict) with value names as keys.'.format(type)
    assert len(value_map) > 0, \
        '{} values must be an mapping (dict) with value names as keys.'.format(type)
    values = []
    for value_name, value in value_map.items():
        assert_valid_name(value_name)
        assert isinstance(value, GraphQLEnumValue), \
            '{}.{} must refer to an object of GraphQLEnumValue type but got: {}'.format(type, value_name, value)
        value.name = value_name
        values.append(value)
    return values


class GraphQLEnumValue(object):
    def __init__(self, value=None, deprecation_reason=None,
                 description=None):
        self.value = value
        self.deprecation_reason = deprecation_reason
        self.description = description


class GraphQLInputObjectType(GraphQLType):
    """Input Object Type Definition

    An input object defines a structured collection of fields which may be
    supplied to a field argument.

    Using `NonNull` will ensure that a value must be provided by the query

    Example:

        NonNullFloat = GraphQLNonNull(GraphQLFloat())

        class GeoPoint(GraphQLInputObjectType):
            name = 'GeoPoint'
            fields = {
                'lat': GraphQLInputObjectField(NonNullFloat),
                'lon': GraphQLInputObjectField(NonNullFloat),
                'alt': GraphQLInputObjectField(GraphQLFloat(),
                    default_value=0)
            }
    """
    def __init__(self, name, fields, description=None):
        assert name, 'Type must be named.'
        assert_valid_name(name)
        self.name = name
        self.description = description
        self._fields = fields
        self._field_map = None

    def get_fields(self):
        if self._field_map is None:
            self._field_map = self._define_field_map(self._fields)
        return self._field_map

    def _define_field_map(self, fields):
        if callable(fields):
            fields = fields()
        assert isinstance(fields, collections.Mapping), (
            '{} fields must be an mapping (dict) with field names as keys or a '
            'function which returns such an mapping.'
        ).format(self)
        assert len(fields) > 0, (
            '{} fields must be an mapping (dict) with field names as keys or a '
            'function which returns such an mapping.'
        ).format(self)

        field_map = {}
        for field_name, field in fields.items():
            assert_valid_name(field_name)
            field = copy.copy(field)
            field.name = field_name
            assert is_input_type(field.type), \
                '{}.{} field type must be Input Type but got: {}'.format(type, field_name, field.type)
            field_map[field_name] = field
        return field_map


class GraphQLInputObjectField(object):
    def __init__(self, type, default_value=None, description=None):
        self.type = type
        self.default_value = default_value
        self.description = description


class GraphQLList(GraphQLType):
    """List Modifier

    A list is a kind of type marker, a wrapping type which points to another
    type. Lists are often created within the context of defining the fields
    of an object type.

    Example:

        class PersonType(GraphQLObjectType):
            name = 'Person'

            def get_fields(self):
                return {
                    'parents': GraphQLField(GraphQLList(PersonType())),
                    'children': GraphQLField(GraphQLList(PersonType())),
                }
    """
    def __init__(self, type):
        assert isinstance(type, GraphQLType), \
            'Can only create List of a GraphQLType but got: {}.'.format(type)
        self.of_type = type

    def __str__(self):
        return '[' + str(self.of_type) + ']'

    def is_same_type(self, other):
        return isinstance(other, GraphQLList) and self.of_type.is_same_type(other.of_type)


class GraphQLNonNull(GraphQLType):
    """Non-Null Modifier

    A non-null is a kind of type marker, a wrapping type which points to another type. Non-null types enforce that their values are never null
    and can ensure an error is raised if this ever occurs during a request. It is useful for fields which you can make a strong guarantee on
    non-nullability, for example usually the id field of a database row will never be null.

    Example:

        class RowType(GraphQLObjectType):
            name = 'Row'
            fields = {
                'id': GraphQLField(type=GraphQLNonNull(GraphQLString()))
            }

    Note: the enforcement of non-nullability occurs within the executor.
    """
    def __init__(self, type):
        assert isinstance(type, GraphQLType) and not isinstance(type, GraphQLNonNull), \
            'Can only create NonNull of a Nullable GraphQLType but got: {}.'.format(type)
        self.of_type = type

    def __str__(self):
        return str(self.of_type) + '!'

    def is_same_type(self, other):
        return isinstance(other, GraphQLNonNull) and self.of_type.is_same_type(other.of_type)
