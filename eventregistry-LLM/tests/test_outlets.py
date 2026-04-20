from eventregistry_llm.outlets import identify_outlet


def test_identify_outlet_from_domain() -> None:
    assert identify_outlet("RTV Slovenija", "rtvslo.si", "https://www.rtvslo.si/foo") == "rtv"
    assert identify_outlet("24ur", "", "https://www.24ur.com/bar") == "24ur"
    assert identify_outlet("Unknown", "example.com", "https://example.com") is None

