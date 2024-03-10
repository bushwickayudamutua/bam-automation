import requests

from bam_core.settings import OPEN_COLLECTIVE_ACCESS_TOKEN

OPEN_COLLECTIVE_API_URL = "https://api.opencollective.com/graphql/v2"

class OpenCollective(object):
    
    def __init__(self, access_token=OPEN_COLLECTIVE_ACCESS_TOKEN):
        self.access_token = access_token
    
    def _graphql_request(self, graphql_query, **variables):
        headers = {
            "Content-Type": "application/json",
            "Personal-Token": self.access_token,
        }
        response = requests.post(
            OPEN_COLLECTIVE_API_URL,
            json={"query": graphql_query, "variables": variables},
            headers=headers,
        )
        try:
            response.raise_for_status()
        except:
            raise Exception(response.text)
        return response.json()

if __name__ == "__main__":
    query = """
query account($slug: String) {
  account(slug: $slug) {
    name
    slug
    members(role: BACKER, limit: 500) {
      totalCount
      nodes {
        account {
          name
          slug
          parentAccount { 
            emails
          }
        }
      }
    }
  }
}
"""
    oc = OpenCollective()
    result = oc._graphql_request(query, slug="bushwick-ayuda-mutua")
    print(result)
    