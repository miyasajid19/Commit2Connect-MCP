from fastmcp.resources import resource

@resource("data://profile")
def profile_resource():
    return {
        "name":"Sajid Miya",
        "title":"AI Engineer",
        "github":"miyasajid19",
        "website":"https://sajidmiya.tech",
        "linkedin":"https://www.linkedin.com/in/sajidmiya",
        "email":"miyasajid19@gmail.com"
    }