from pytest import raises
from graphql.core.type import (
    GraphQLSchema,
    GraphQLScalarType,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLUnionType,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLString,
    GraphQLField,
    GraphQLEnumValue,
    GraphQLInputObjectField,
    GraphQLArgument)


SomeScalarType = GraphQLScalarType(
    name='SomeScalar',
    serialize=lambda *args: None,
    parse_value=lambda *args: None,
    parse_literal=lambda *args: None,
)

SomeObjectType = GraphQLObjectType(
    name='SomeObject',
    fields={'f': GraphQLField(GraphQLString)},
)

ObjectWithIsTypeOf = GraphQLObjectType(
    name='ObjectWithIsTypeOf',
    is_type_of=lambda *args: True,
    fields={'f': GraphQLField(GraphQLString)},
)

SomeUnionType = GraphQLUnionType(
    name='SomeUnion',
    resolve_type=lambda *args: None,
    types=[SomeObjectType],
)

SomeInterfaceType = GraphQLInterfaceType(
    name='SomeInterface',
    resolve_type=lambda *args: None,
    fields={'f': GraphQLField(GraphQLString)},
)

SomeEnumType = GraphQLEnumType(
    name='SomeEnum',
    values={
        'ONLY': GraphQLEnumValue()
    },
)

SomeInputObjectType = GraphQLInputObjectType(
    name='SomeInputObject',
    fields={
        'val': GraphQLInputObjectField(type=GraphQLString, default_value='hello'),
    },
)


def with_modifiers(types):
    return (types +
            list(map(GraphQLList, types)) +
            list(map(GraphQLNonNull, types)) +
            [GraphQLNonNull(GraphQLList(t)) for t in types])


output_types = with_modifiers([
    GraphQLString,
    SomeScalarType,
    SomeEnumType,
    SomeObjectType,
    SomeUnionType,
    SomeInterfaceType,
])

not_output_types = with_modifiers([
    SomeInputObjectType,
]) + [str]

input_types = with_modifiers([
    GraphQLString,
    SomeScalarType,
    SomeEnumType,
    SomeInputObjectType,
])

not_input_types = with_modifiers([
    SomeObjectType,
    SomeUnionType,
    SomeInterfaceType,
]) + [str]


def schema_with_field_type(type):
    return GraphQLSchema(
        query=GraphQLObjectType(
            name='Query',
            fields={'f': GraphQLField(type)},
        )
    )


# noinspection PyMethodMayBeStatic
class TestSchemaMustHaveObjectRootTypes(object):
    def test_accepts_object_type_query(self):
        GraphQLSchema(query=SomeObjectType)

    def test_accepts_object_type_query_and_mutation(self):
        MutationType = GraphQLObjectType(
            name='Mutation',
            fields={'edit': GraphQLField(GraphQLString)},
        )
        GraphQLSchema(query=SomeObjectType, mutation=MutationType)

    def test_rejects_no_query_type(self):
        # Enforced by function signature
        with raises(TypeError):
            GraphQLSchema()

    def test_rejects_input_type_query(self):
        with raises(AssertionError) as excinfo:
            GraphQLSchema(query=SomeInputObjectType)
        assert 'Schema query must be Object Type but got: SomeInputObject.' == str(excinfo.value)

    def test_rejects_input_type_mutation(self):
        with raises(AssertionError) as excinfo:
            GraphQLSchema(query=SomeObjectType, mutation=SomeInputObjectType)
        assert 'Schema mutation must be Object Type but got: SomeInputObject.' == str(excinfo.value)


# noinspection PyMethodMayBeStatic
class TestSchemaMustContainUniquelyNamedTypes(object):
    def test_rejects_builtin_type_redefinition(self):
        FakeString = GraphQLScalarType(
            name='String',
            serialize=lambda *args: None,
        )
        QueryType = GraphQLObjectType(
            name='Query',
            fields={
                'normal': GraphQLField(GraphQLString),
                'fake': GraphQLField(FakeString),
            },
        )
        with raises(AssertionError) as excinfo:
            GraphQLSchema(query=QueryType)
        assert 'Schema must contain unique named types but contains multiple types named "String".' == str(excinfo.value)

    def test_rejects_object_type_duplicate(self):
        A = GraphQLObjectType(
            name='SameName',
            fields={'f': GraphQLField(GraphQLString)},
        )
        B = GraphQLObjectType(
            name='SameName',
            fields={'f': GraphQLField(GraphQLString)},
        )
        QueryType = GraphQLObjectType(
            name='Query',
            fields={
                'a': GraphQLField(A),
                'b': GraphQLField(B),
            }
        )
        with raises(AssertionError) as excinfo:
            GraphQLSchema(query=QueryType)
        assert 'Schema must contain unique named types but contains multiple types named "SameName".' == str(excinfo.value)

    def test_rejects_same_named_objects_implementing_iface(self):
        AnotherInterface = GraphQLInterfaceType(
            name='AnotherInterface',
            resolve_type=lambda *args: None,
            fields={'f': GraphQLField(GraphQLString)},
        )

        # Automatically included in Interface
        FirstBadObject = GraphQLObjectType(
            name='BadObject',
            interfaces=[AnotherInterface],
            fields={'f': GraphQLField(GraphQLString)},
        )

        # Automatically included in Interface
        SecondBadObject = GraphQLObjectType(
            name='BadObject',
            interfaces=[AnotherInterface],
            fields={'f': GraphQLField(GraphQLString)},
        )

        QueryType = GraphQLObjectType(
            name='Query',
            fields={'iface': GraphQLField(AnotherInterface)},
        )

        with raises(AssertionError) as excinfo:
            GraphQLSchema(query=QueryType)
        assert 'Schema must contain unique named types but contains multiple types named "BadObject".' == str(excinfo.value)


# noinspection PyMethodMayBeStatic
class TestObjectsMustHaveFields(object):
    def test_accepts_fields_dict(self):
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            fields={'f': GraphQLField(GraphQLString)},
        ))

    def test_accepts_fields_function(self):
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            fields=lambda: {
                'f': GraphQLField(GraphQLString),
            },
        ))

    def test_rejects_missing_fields(self):
        # Enforced by function signature
        with raises(TypeError):
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
            ))

    def test_rejects_incorrectly_named_fields(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                fields={'bad-name-with-dashes': GraphQLField(GraphQLString)},
            ))
        assert 'Names must match /^[_a-zA-Z][_a-zA-Z0-9]*$/ but "bad-name-with-dashes" does not.' == str(excinfo.value)

    def test_rejects_incorrectly_typed_fields(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                fields=[{'bad-name-with-dashes': GraphQLField(GraphQLString)}],
            ))
        assert 'SomeObject fields must be an mapping (dict) with field names as keys or a ' \
               'function which returns such an mapping.' == str(excinfo.value)

    def test_rejects_empty_fields(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                fields={},
            ))
        assert 'SomeObject fields must be an mapping (dict) with field names as keys or a ' \
               'function which returns such an mapping.' == str(excinfo.value)

    def test_rejects_function_returns_nothing(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                fields=lambda: None,
            ))
        assert 'SomeObject fields must be an mapping (dict) with field names as keys or a ' \
               'function which returns such an mapping.' == str(excinfo.value)

    def test_rejects_function_returns_empty(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                fields=lambda: {},
            ))
        assert 'SomeObject fields must be an mapping (dict) with field names as keys or a ' \
               'function which returns such an mapping.' == str(excinfo.value)


# noinspection PyMethodMayBeStatic
class TestFieldsArgsNaming(object):
    def test_accepts_valid_names(self):
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            fields={
                'goodField': GraphQLField(
                    type=GraphQLString,
                    args={
                        'goodArg': GraphQLArgument(GraphQLString),
                    }
                )
            },
        ))

    def test_rejects_invalid_names(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                fields={
                    'badField': GraphQLField(
                        type=GraphQLString,
                        args={
                            'bad-name-with-dashes': GraphQLArgument(GraphQLString),
                        }
                    )
                },
            ))
        assert 'Names must match /^[_a-zA-Z][_a-zA-Z0-9]*$/ but "bad-name-with-dashes" does not.' == str(excinfo.value)


# noinspection PyMethodMayBeStatic
class TestFieldsArgsMustBeObjects(object):
    def test_accepts_field_args(self):
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            fields={
                'goodField': GraphQLField(
                    type=GraphQLString,
                    args={
                        'goodArg': GraphQLArgument(GraphQLString),
                    }
                )
            },
        ))

    def test_rejects_incorrect_type(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                fields={
                    'badField': GraphQLField(
                        type=GraphQLString,
                        args=[
                            {'badArg': GraphQLString},
                        ]
                    )
                },
            ))
        assert 'SomeObject.badField args must be an mapping (dict) with argument names as keys.' == str(excinfo.value)


# noinspection PyMethodMayBeStatic
class TestObjectIfacesMustBeList(object):
    def test_accepts_list_ifaces(self):
        AnotherInterfaceType = GraphQLInterfaceType(
            name='AnotherInterface',
            resolve_type=lambda *args: None,
            fields={'f': GraphQLField(GraphQLString)},
        )
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            interfaces=[AnotherInterfaceType],
            fields={'f': GraphQLField(GraphQLString)},
        ))

    def test_accepts_ifaces_as_function_returning_list(self):
        AnotherInterfaceType = GraphQLInterfaceType(
            name='AnotherInterface',
            resolve_type=lambda *args: None,
            fields={'f': GraphQLField(GraphQLString)},
        )
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            interfaces=lambda: [AnotherInterfaceType],
            fields={'f': GraphQLField(GraphQLString)},
        ))

    def test_accepts_tuple_ifaces(self):
        AnotherInterfaceType = GraphQLInterfaceType(
            name='AnotherInterface',
            resolve_type=lambda *args: None,
            fields={'f': GraphQLField(GraphQLString)},
        )
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            interfaces=(AnotherInterfaceType, ),
            fields={'f': GraphQLField(GraphQLString)},
        ))

    def test_accepts_ifaces_as_function_returning_tuple(self):
        AnotherInterfaceType = GraphQLInterfaceType(
            name='AnotherInterface',
            resolve_type=lambda *args: None,
            fields={'f': GraphQLField(GraphQLString)},
        )
        schema_with_field_type(GraphQLObjectType(
            name='SomeObject',
            interfaces=lambda: (AnotherInterfaceType, ),
            fields={'f': GraphQLField(GraphQLString)},
        ))

    def test_rejects_incorrectly_typed_ifaces(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                interfaces={},
                fields={'f': GraphQLField(GraphQLString)},
            ))
        assert 'SomeObject interfaces must be an list/tuple or a function which returns an list/tuple.' == str(excinfo.value)

    def test_rejects_func_returning_incorrectly_typed_ifaces(self):
        with raises(AssertionError) as excinfo:
            schema_with_field_type(GraphQLObjectType(
                name='SomeObject',
                interfaces=lambda: {},
                fields={'f': GraphQLField(GraphQLString)},
            ))
        assert 'SomeObject interfaces must be an list/tuple or a function which returns an list/tuple.' == str(excinfo.value)

"""describe('Type System: Union types must be array', () => {

    it('accepts a Union type with array types', () => {
    expect(
        () => schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    resolveType: () => null,
                       types: [ SomeObjectType ],
}))
).not.to.throw();
});

it('rejects a Union type without types', () => {
    expect(
        () => schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    resolveType: () => null,
}))
).to.throw(
    'Must provide Array of types for Union SomeUnion.'
);
});

it('rejects a Union type with empty types', () => {
    expect(
        () => schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    resolveType: () => null,
                       types: []
}))
).to.throw(
    'Must provide Array of types for Union SomeUnion.'
);
});

it('rejects a Union type with incorrectly typed types', () => {
    expect(
        () => schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    resolveType: () => null,
                       types: {
SomeObjectType
},
}))
).to.throw(
    'Must provide Array of types for Union SomeUnion.'
);
});

});


describe('Type System: Input Objects must have fields', () => {

    function schemaWithInputObject(inputObjectType) {
return new GraphQLSchema({
    query: new GraphQLObjectType({
    name: 'Query',
    fields: {
        f: {
            type: GraphQLString,
            args: {
                badArg: { type: inputObjectType }
            }
        }
    }
})
});
}

it('accepts an Input Object type with fields', () => {
    expect(
        () => schemaWithInputObject(new GraphQLInputObjectType({
    name: 'SomeInputObject',
    fields: {
        f: { type: GraphQLString }
    }
}))
).not.to.throw();
});

it('accepts an Input Object type with a field function', () => {
    expect(
        () => schemaWithInputObject(new GraphQLInputObjectType({
    name: 'SomeInputObject',
    fields() {
return {
    f: { type: GraphQLString }
};
}
}))
).not.to.throw();
});

it('rejects an Input Object type with missing fields', () => {
    expect(
        () => schemaWithInputObject(new GraphQLInputObjectType({
    name: 'SomeInputObject',
    }))
).to.throw(
    'SomeInputObject fields must be an object with field names as keys or a ' +
    'function which returns such an object.'
);
});

it('rejects an Input Object type with incorrectly typed fields', () => {
    expect(
        () => schemaWithInputObject(new GraphQLInputObjectType({
    name: 'SomeInputObject',
    fields: [
{ field: GraphQLString }
]
}))
).to.throw(
    'SomeInputObject fields must be an object with field names as keys or a ' +
    'function which returns such an object.'
);
});

it('rejects an Input Object type with empty fields', () => {
    expect(
        () => schemaWithInputObject(new GraphQLInputObjectType({
    name: 'SomeInputObject',
    fields: {}
}))
).to.throw(
    'SomeInputObject fields must be an object with field names as keys or a ' +
    'function which returns such an object.'
);
});

it('rejects an Input Object type with a field function that returns nothing', () => {
    expect(
        () => schemaWithInputObject(new GraphQLInputObjectType({
    name: 'SomeInputObject',
    fields() {
return;
}
}))
).to.throw(
    'SomeInputObject fields must be an object with field names as keys or a ' +
    'function which returns such an object.'
);
});

it('rejects an Input Object type with a field function that returns empty', () => {
    expect(
        () => schemaWithInputObject(new GraphQLInputObjectType({
    name: 'SomeInputObject',
    fields() {
return {};
}
}))
).to.throw(
    'SomeInputObject fields must be an object with field names as keys or a ' +
    'function which returns such an object.'
);
});

});


describe('Type System: Object types must be assertable', () => {

    it('accepts an Object type with an isTypeOf function', () => {
    expect(() => {
    schemaWithFieldType(new GraphQLObjectType({
name: 'AnotherObject',
isTypeOf: () => true,
fields: { f: { type: GraphQLString } }
}));
}).not.to.throw();
});

it('rejects an Object type with an incorrect type for isTypeOf', () => {
    expect(() => {
    schemaWithFieldType(new GraphQLObjectType({
name: 'AnotherObject',
isTypeOf: {},
fields: { f: { type: GraphQLString } }
}));
}).to.throw(
    'AnotherObject must provide "isTypeOf" as a function.'
);
});

});


describe('Type System: Interface types must be resolvable', () => {

    it('accepts an Interface type defining resolveType', () => {
    expect(() => {
    var AnotherInterfaceType = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: { f: { type: GraphQLString } }
});

schemaWithFieldType(new GraphQLObjectType({
name: 'SomeObject',
interfaces: [ AnotherInterfaceType ],
fields: { f: { type: GraphQLString } }
}));
}).not.to.throw();
});

it('accepts an Interface with implementing type defining isTypeOf', () => {
    expect(() => {
    var InterfaceTypeWithoutResolveType = new GraphQLInterfaceType({
    name: 'InterfaceTypeWithoutResolveType',
    fields: { f: { type: GraphQLString } }
});

schemaWithFieldType(new GraphQLObjectType({
name: 'SomeObject',
isTypeOf: () => true,
interfaces: [ InterfaceTypeWithoutResolveType ],
fields: { f: { type: GraphQLString } }
}));
}).not.to.throw();
});

it('accepts an Interface type defining resolveType with implementing type defining isTypeOf', () => {
    expect(() => {
    var AnotherInterfaceType = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: { f: { type: GraphQLString } }
});

schemaWithFieldType(new GraphQLObjectType({
name: 'SomeObject',
isTypeOf: () => true,
interfaces: [ AnotherInterfaceType ],
fields: { f: { type: GraphQLString } }
}));
}).not.to.throw();
});

it('rejects an Interface type with an incorrect type for resolveType', () => {
    expect(() =>
new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: {},
    fields: { f: { type: GraphQLString } }
})
).to.throw(
    'AnotherInterface must provide "resolveType" as a function.'
);
});

it('rejects an Interface type not defining resolveType with implementing type not defining isTypeOf', () => {
    expect(() => {
    var InterfaceTypeWithoutResolveType = new GraphQLInterfaceType({
    name: 'InterfaceTypeWithoutResolveType',
    fields: { f: { type: GraphQLString } }
});

schemaWithFieldType(new GraphQLObjectType({
name: 'SomeObject',
interfaces: [ InterfaceTypeWithoutResolveType ],
fields: { f: { type: GraphQLString } }
}));
}).to.throw(
    'Interface Type InterfaceTypeWithoutResolveType does not provide a ' +
    '"resolveType" function and implementing Type SomeObject does not ' +
    'provide a "isTypeOf" function. ' +
    'There is no way to resolve this implementing type during execution.'
);
});

});


describe('Type System: Union types must be resolvable', () => {

    it('accepts a Union type defining resolveType', () => {
    expect(() =>
schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    resolveType: () => null,
                       types: [ SomeObjectType ],
}))
).not.to.throw();
});

it('accepts a Union of Object types defining isTypeOf', () => {
    expect(() =>
schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    types: [ ObjectWithIsTypeOf ],
    }))
).not.to.throw();
});

it('accepts a Union type defining resolveType of Object types defining isTypeOf', () => {
    expect(() =>
schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    resolveType: () => null,
                       types: [ ObjectWithIsTypeOf ],
}))
).not.to.throw();
});

it('rejects an Interface type with an incorrect type for resolveType', () => {
    expect(() =>
schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    resolveType: {},
    types: [ ObjectWithIsTypeOf ],
    }))
).to.throw(
    'SomeUnion must provide "resolveType" as a function.'
);
});

it('rejects a Union type not defining resolveType of Object types not defining isTypeOf', () => {
    expect(() =>
schemaWithFieldType(new GraphQLUnionType({
    name: 'SomeUnion',
    types: [ SomeObjectType ],
    }))
).to.throw(
    'Union Type SomeUnion does not provide a "resolveType" function and ' +
    'possible Type SomeObject does not provide a "isTypeOf" function. ' +
    'There is no way to resolve this possible type during execution.'
);
});

});


describe('Type System: Scalar types must be serializable', () => {

    it('accepts a Scalar type defining serialize', () => {
    expect(() =>
schemaWithFieldType(new GraphQLScalarType({
    name: 'SomeScalar',
    serialize: () => null,
}))
).not.to.throw();
});

it('rejects a Scalar type not defining serialize', () => {
    expect(() =>
schemaWithFieldType(new GraphQLScalarType({
    name: 'SomeScalar',
    }))
).to.throw(
    'SomeScalar must provide "serialize" function. If this custom Scalar ' +
    'is also used as an input type, ensure "parseValue" and "parseLiteral" ' +
    'functions are also provided.'
);
});

it('rejects a Scalar type defining serialize with an incorrect type', () => {
    expect(() =>
schemaWithFieldType(new GraphQLScalarType({
    name: 'SomeScalar',
    serialize: {}
}))
).to.throw(
    'SomeScalar must provide "serialize" function. If this custom Scalar ' +
    'is also used as an input type, ensure "parseValue" and "parseLiteral" ' +
    'functions are also provided.'
);
});

it('accepts a Scalar type defining parseValue and parseLiteral', () => {
    expect(() =>
schemaWithFieldType(new GraphQLScalarType({
    name: 'SomeScalar',
    serialize: () => null,
                     parseValue: () => null,
                                       parseLiteral: () => null,
}))
).not.to.throw();
});

it('rejects a Scalar type defining parseValue but not parseLiteral', () => {
    expect(() =>
schemaWithFieldType(new GraphQLScalarType({
    name: 'SomeScalar',
    serialize: () => null,
                     parseValue: () => null,
}))
).to.throw(
    'SomeScalar must provide both "parseValue" and "parseLiteral" functions.'
);
});

it('rejects a Scalar type defining parseLiteral but not parseValue', () => {
    expect(() =>
schemaWithFieldType(new GraphQLScalarType({
    name: 'SomeScalar',
    serialize: () => null,
                     parseLiteral: () => null,
}))
).to.throw(
    'SomeScalar must provide both "parseValue" and "parseLiteral" functions.'
);
});

it('rejects a Scalar type defining parseValue and parseLiteral with an incorrect type', () => {
    expect(() =>
schemaWithFieldType(new GraphQLScalarType({
    name: 'SomeScalar',
    serialize: () => null,
                     parseValue: {},
parseLiteral: {},
}))
).to.throw(
    'SomeScalar must provide both "parseValue" and "parseLiteral" functions.'
);
});

});


describe('Type System: Enum types must be well defined', () => {

    it('accepts a well defined Enum type with empty value definition', () => {
    expect(() =>
new GraphQLEnumType({
    name: 'SomeEnum',
    values: {
        FOO: {},
        BAR: {},
        }
})
).not.to.throw();
});

it('accepts a well defined Enum type with internal value definition', () => {
    expect(() =>
new GraphQLEnumType({
    name: 'SomeEnum',
    values: {
        FOO: { value: 10 },
        BAR: { value: 20 },
        }
})
).not.to.throw();
});

it('rejects an Enum type without values', () => {
    expect(() =>
new GraphQLEnumType({
    name: 'SomeEnum',
    })
).to.throw(
    'SomeEnum values must be an object with value names as keys.'
);
});

it('rejects an Enum type with empty values', () => {
    expect(() =>
new GraphQLEnumType({
    name: 'SomeEnum',
    values: {}
})
).to.throw(
    'SomeEnum values must be an object with value names as keys.'
);
});

it('rejects an Enum type with incorrectly typed values', () => {
    expect(() =>
new GraphQLEnumType({
    name: 'SomeEnum',
    values: [
        { FOO: 10 }
    ]
})
).to.throw(
    'SomeEnum values must be an object with value names as keys.'
);
});

it('rejects an Enum type with missing value definition', () => {
    expect(() =>
new GraphQLEnumType({
    name: 'SomeEnum',
    values: {
        FOO: null
    }
})
).to.throw(
    'SomeEnum.FOO must refer to an object with a "value" key representing ' +
    'an internal value but got: null.'
);
});

it('rejects an Enum type with incorrectly typed value definition', () => {
    expect(() =>
new GraphQLEnumType({
    name: 'SomeEnum',
    values: {
        FOO: 10
    }
})
).to.throw(
    'SomeEnum.FOO must refer to an object with a "value" key representing ' +
    'an internal value but got: 10.'
);
});

});


describe('Type System: Object fields must have output types', () => {

    function schemaWithObjectFieldOfType(fieldType) {
    var BadObjectType = new GraphQLObjectType({
    name: 'BadObject',
    fields: {
        badField: { type: fieldType }
    }
});

return new GraphQLSchema({
    query: new GraphQLObjectType({
    name: 'Query',
    fields: {
        f: { type: BadObjectType }
    }
})
});
}

outputTypes.forEach(type => {
    it(`accepts an output type as an Object field type: ${type}`, () => {
    expect(() => schemaWithObjectFieldOfType(type)).not.to.throw();
});
});

it('rejects an empty Object field type', () => {
    expect(() => schemaWithObjectFieldOfType(undefined)).to.throw(
    'BadObject.badField field type must be Output Type but got: undefined.'
);
});

notOutputTypes.forEach(type => {
    it(`rejects a non-output type as an Object field type: ${type}`, () => {
    expect(() => schemaWithObjectFieldOfType(type)).to.throw(
    `BadObject.badField field type must be Output Type but got: ${type}.`
);
});
});

});


describe('Type System: Objects can only implement interfaces', () => {

    function schemaWithObjectImplementingType(implementedType) {
var BadObjectType = new GraphQLObjectType({
    name: 'BadObject',
    interfaces: [ implementedType ],
    fields: { f: { type: GraphQLString } }
});

return new GraphQLSchema({
    query: new GraphQLObjectType({
    name: 'Query',
    fields: {
        f: { type: BadObjectType }
    }
})
});
}

it('accepts an Object implementing an Interface', () => {
    expect(() => {
    var AnotherInterfaceType = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: { f: { type: GraphQLString } }
});

schemaWithObjectImplementingType(AnotherInterfaceType);
}).not.to.throw();
});

var notInterfaceTypes = withModifiers([
    SomeScalarType,
    SomeEnumType,
    SomeObjectType,
    SomeUnionType,
    SomeInputObjectType,
    ]);

notInterfaceTypes.forEach(type => {
    it(`rejects an Object implementing a non-Interface type: ${type}`, () => {
    expect(() => schemaWithObjectImplementingType(type)).to.throw(
    `BadObject may only implement Interface types, it cannot implement: ${type}.`
);
});
});

});


describe('Type System: Unions must represent Object types', () => {

    function schemaWithUnionOfType(type) {
var BadUnionType = new GraphQLUnionType({
    name: 'BadUnion',
    resolveType: () => null,
                       types: [ type ],
});

return new GraphQLSchema({
    query: new GraphQLObjectType({
    name: 'Query',
    fields: {
        f: { type: BadUnionType }
    }
})
});
}

it('accepts a Union of an Object Type', () => {
    expect(() =>
schemaWithUnionOfType(SomeObjectType)
).not.to.throw();
});

var notObjectTypes = withModifiers([
    SomeScalarType,
    SomeEnumType,
    SomeInterfaceType,
    SomeUnionType,
    SomeInputObjectType,
    ]);

notObjectTypes.forEach(type => {
    it(`rejects a Union of a non-Object type: ${type}`, () => {
    expect(() => schemaWithUnionOfType(type)).to.throw(
    `BadUnion may only contain Object types, it cannot contain: ${type}.`
);
});
});

});


describe('Type System: Interface fields must have output types', () => {

    function schemaWithInterfaceFieldOfType(fieldType) {
var BadInterfaceType = new GraphQLInterfaceType({
    name: 'BadInterface',
    fields: {
        badField: { type: fieldType }
    }
});

return new GraphQLSchema({
    query: new GraphQLObjectType({
    name: 'Query',
    fields: {
        f: { type: BadInterfaceType }
    }
})
});
}

outputTypes.forEach(type => {
    it(`accepts an output type as an Interface field type: ${type}`, () => {
    expect(() => schemaWithInterfaceFieldOfType(type)).not.to.throw();
});
});

it('rejects an empty Interface field type', () => {
    expect(() => schemaWithInterfaceFieldOfType(undefined)).to.throw(
    'BadInterface.badField field type must be Output Type but got: undefined.'
);
});

notOutputTypes.forEach(type => {
    it(`rejects a non-output type as an Interface field type: ${type}`, () => {
    expect(() => schemaWithInterfaceFieldOfType(type)).to.throw(
    `BadInterface.badField field type must be Output Type but got: ${type}.`
);
});
});

});


describe('Type System: Field arguments must have input types', () => {

    function schemaWithArgOfType(argType) {
var BadObjectType = new GraphQLObjectType({
    name: 'BadObject',
    fields: {
        badField: {
            type: GraphQLString,
            args: {
                badArg: { type: argType }
            }
        }
    }
});

return new GraphQLSchema({
    query: new GraphQLObjectType({
    name: 'Query',
    fields: {
        f: { type: BadObjectType }
    }
})
});
}

inputTypes.forEach(type => {
    it(`accepts an input type as a field arg type: ${type}`, () => {
    expect(() => schemaWithArgOfType(type)).not.to.throw();
});
});

it('rejects an empty field arg type', () => {
    expect(() => schemaWithArgOfType(undefined)).to.throw(
    'BadObject.badField(badArg:) argument type must be Input Type but got: undefined.'
);
});

notInputTypes.forEach(type => {
    it(`rejects a non-input type as a field arg type: ${type}`, () => {
    expect(() => schemaWithArgOfType(type)).to.throw(
    `BadObject.badField(badArg:) argument type must be Input Type but got: ${type}.`
);
});
});

});


describe('Type System: Input Object fields must have input types', () => {

    function schemaWithInputFieldOfType(inputFieldType) {
var BadInputObjectType = new GraphQLInputObjectType({
    name: 'BadInputObject',
    fields: {
        badField: { type: inputFieldType }
    }
});

return new GraphQLSchema({
    query: new GraphQLObjectType({
    name: 'Query',
    fields: {
        f: {
            type: GraphQLString,
            args: {
                badArg: { type: BadInputObjectType }
            }
        }
    }
})
});
}

inputTypes.forEach(type => {
    it(`accepts an input type as an input field type: ${type}`, () => {
    expect(() => schemaWithInputFieldOfType(type)).not.to.throw();
});
});

it('rejects an empty input field type', () => {
    expect(() => schemaWithInputFieldOfType(undefined)).to.throw(
    'BadInputObject.badField field type must be Input Type but got: undefined.'
);
});

notInputTypes.forEach(type => {
    it(`rejects a non-input type as an input field type: ${type}`, () => {
    expect(() => schemaWithInputFieldOfType(type)).to.throw(
    `BadInputObject.badField field type must be Input Type but got: ${type}.`
);
});
});

});


describe('Type System: List must accept GraphQL types', () => {

    var types = withModifiers([
    GraphQLString,
    SomeScalarType,
    SomeObjectType,
    SomeUnionType,
    SomeInterfaceType,
    SomeEnumType,
    SomeInputObjectType,
    ]);

var notTypes = [
{},
String,
undefined,
null,
];

types.forEach(type => {
    it(`accepts an type as item type of list: ${type}`, () => {
    expect(() => new GraphQLList(type)).not.to.throw();
});
});

notTypes.forEach(type => {
    it(`rejects a non-type as item type of list: ${type}`, () => {
    expect(() => new GraphQLList(type)).to.throw(
    `Can only create List of a GraphQLType but got: ${type}.`
);
});
});

});


describe('Type System: NonNull must accept GraphQL types', () => {

    var nullableTypes = [
GraphQLString,
SomeScalarType,
SomeObjectType,
SomeUnionType,
SomeInterfaceType,
SomeEnumType,
SomeInputObjectType,
new GraphQLList(GraphQLString),
new GraphQLList(new GraphQLNonNull(GraphQLString)),
];

var notNullableTypes = [
new GraphQLNonNull(GraphQLString),
{},
String,
undefined,
null,
];

nullableTypes.forEach(type => {
    it(`accepts an type as nullable type of non-null: ${type}`, () => {
    expect(() => new GraphQLNonNull(type)).not.to.throw();
});
});

notNullableTypes.forEach(type => {
    it(`rejects a non-type as nullable type of non-null: ${type}`, () => {
    expect(() => new GraphQLNonNull(type)).to.throw(
    `Can only create NonNull of a Nullable GraphQLType but got: ${type}.`
);
});
});

});


describe('Objects must adhere to Interface they implement', () => {

    it('accepts an Object which implements an Interface', () => {
    expect(() => {
    var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: {
        type: GraphQLString,
        args: {
            input: { type: GraphQLString }
        }
    }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: {
            type: GraphQLString,
            args: {
                input: { type: GraphQLString }
            }
        }
    }
});

return schemaWithFieldType(AnotherObject);
}).not.to.throw();
});

it('accepts an Object which implements an Interface along with more fields', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: {
        type: GraphQLString,
        args: {
            input: { type: GraphQLString },
            }
    }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: {
            type: GraphQLString,
            args: {
                input: { type: GraphQLString },
                }
        },
        anotherfield: { type: GraphQLString }
    }
});

return schemaWithFieldType(AnotherObject);
}).not.to.throw();
});

it('rejects an Object which implements an Interface field along with more arguments', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: {
        type: GraphQLString,
        args: {
            input: { type: GraphQLString },
            }
    }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: {
            type: GraphQLString,
            args: {
                input: { type: GraphQLString },
                anotherInput: { type: GraphQLString },
                }
        }
    }
});

return schemaWithFieldType(AnotherObject);
}).to.throw(
    'AnotherInterface.field does not define argument "anotherInput" but ' +
    'AnotherObject.field provides it.'
);
});

it('rejects an Object missing an Interface field', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: {
        type: GraphQLString,
        args: {
            input: { type: GraphQLString },
            }
    }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        anotherfield: { type: GraphQLString }
    }
});

return schemaWithFieldType(AnotherObject);
}).to.throw(
    '"AnotherInterface" expects field "field" but ' +
    '"AnotherObject" does not provide it.'
);
});

it('rejects an Object with an incorrectly typed Interface field', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: {
        type: GraphQLString,
        args: {
            input: { type: GraphQLString },
            }
    }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: {
            type: SomeScalarType,
            args: {
                input: { type: GraphQLString },
                }
        }
    }
});

return schemaWithFieldType(AnotherObject);
}).to.throw(
    'AnotherInterface.field expects type "String" but ' +
    'AnotherObject.field provides type "SomeScalar".'
);
});

it('rejects an Object missing an Interface argument', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: {
        type: GraphQLString,
        args: {
            input: { type: GraphQLString },
            }
    }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: {
            type: GraphQLString,
            }
    }
});

return schemaWithFieldType(AnotherObject);
}).to.throw(
    'AnotherInterface.field expects argument "input" but ' +
    'AnotherObject.field does not provide it.'
);
});

it('rejects an Object with an incorrectly typed Interface argument', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: {
        type: GraphQLString,
        args: {
            input: { type: GraphQLString },
            }
    }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: {
            type: GraphQLString,
            args: {
                input: { type: SomeScalarType },
                }
        }
    }
});

return schemaWithFieldType(AnotherObject);
}).to.throw(
    'AnotherInterface.field(input:) expects type "String" but ' +
    'AnotherObject.field(input:) provides type "SomeScalar".'
);
});

it('accepts an Object with an equivalently modified Interface field type', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: { type: new GraphQLNonNull(new GraphQLList(GraphQLString)) }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: { type: new GraphQLNonNull(new GraphQLList(GraphQLString)) }
}
});

return schemaWithFieldType(AnotherObject);
}).not.to.throw();
});

it('rejects an Object with a differently modified Interface field type', () => {
    expect(() => {
var AnotherInterface = new GraphQLInterfaceType({
    name: 'AnotherInterface',
    resolveType: () => null,
                       fields: {
    field: { type: GraphQLString }
}
});

var AnotherObject = new GraphQLObjectType({
    name: 'AnotherObject',
    interfaces: [ AnotherInterface ],
    fields: {
        field: { type: new GraphQLNonNull(GraphQLString) }
    }
});

return schemaWithFieldType(AnotherObject);
}).to.throw(
    'AnotherInterface.field expects type "String" but ' +
    'AnotherObject.field provides type "String!".'
);
});

});
"""