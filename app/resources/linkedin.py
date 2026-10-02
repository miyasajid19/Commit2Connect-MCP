from fastmcp.resources import resource

@resource("data://profile", tags={"linkedin", "identity"}, version="1.0")
def profile_resource():
    return {
        "name":"Sajid Miya",
        "title":"AI Engineer",
        "github":"miyasajid19",
        "website":["https://sajidmiya.tech","https://www.sajidmiya.com.np"],
        "linkedin":"https://www.linkedin.com/in/sajidmiya",
        "instagram":"https://www.instagram.com/miyasajid19",
        "facebook":"https://www.facebook.com/miyasajid19",
        "email":["miyasajid19@gmail.com","smiya60_be23@thapar.edu"],
    }