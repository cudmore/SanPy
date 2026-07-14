#!/usr/bin/env python3
"""Test script for KymRoiMetaData dataclass conversion."""

from sanpy.kym.kymRoiMetaData import KymRoiMetaData, KymRoiMetaDataFields

def test_basic_functionality():
    """Test basic functionality of the converted KymRoiMetaData."""
    print("Testing KymRoiMetaData dataclass conversion...")
    
    # Test creating an instance with a proper filename format
    metadata = KymRoiMetaData("test/path/20250312 ISAN Control R1 LS1_0001.tif")
    
    # Test getting parameters
    assert metadata.getParam('Animal ID') == ''
    assert metadata.getParam('Region') == 'ISAN'
    assert metadata.getParam('Cell ID') == '20250312 ISAN R1 LS1'
    assert metadata.getParam('Condition') == 'Control'
    assert metadata.getParam('Repeat') == 1
    assert metadata.getParam('Accept') == True
    
    # Test setting parameters
    metadata.setParam('Animal ID', 'test_animal')
    assert metadata.getParam('Animal ID') == 'test_animal'
    
    # Test dictionary-style access
    metadata['Note'] = 'test note'
    assert metadata['Note'] == 'test note'
    
    # Test items() method
    items = list(metadata.items())
    assert len(items) > 0
    assert any(key == 'Animal ID' and value == 'test_animal' for key, value in items)
    
    # Test contains
    assert 'Animal ID' in metadata
    assert 'NonExistent' not in metadata
    
    # Test JSON serialization
    json_str = metadata.toJson()
    assert isinstance(json_str, str)
    assert 'test_animal' in json_str
    
    print("✓ All basic functionality tests passed!")
    
    # Test dataclass fields
    print(f"✓ Dataclass has {len(metadata._fields.__dataclass_fields__)} fields")
    print(f"✓ Field types: {[(name, field.type) for name, field in metadata._fields.__dataclass_fields__.items()]}")

if __name__ == "__main__":
    test_basic_functionality()
    print("\n🎉 KymRoiMetaData dataclass conversion successful!") 