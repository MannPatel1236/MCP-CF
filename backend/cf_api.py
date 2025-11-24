import httpx
import asyncio
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeforcesAPI:
    BASE_URL = "https://codeforces.com/api"
    
    def __init__(self):
        self.last_request_time = 0
        self.rate_limit_delay = 1.0 

    async def _make_request(self, method: str, params: dict = None):
        """
        Internal method to make requests with rate limiting.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
            
        self.last_request_time = time.time()
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/{method}", params=params)
                response.raise_for_status()
                data = response.json()
                
                if data["status"] != "OK":
                    raise Exception(f"Codeforces API Error: {data.get('comment', 'Unknown error')}")
                
                return data["result"]
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e}")
                raise Exception(f"Failed to connect to Codeforces API: {e}")
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                raise

    async def get_user_info(self, handle: str):
        """
        Returns information about one or more users.
        """
        return await self._make_request("user.info", {"handles": handle})

    async def get_user_status(self, handle: str, from_index: int = 1, count: int = 10):
        """
        Returns submissions of specified user.
        """
        return await self._make_request("user.status", {
            "handle": handle,
            "from": from_index,
            "count": count
        })

    async def get_user_rating(self, handle: str):
        """
        Returns rating history of the specified user.
        """
        return await self._make_request("user.rating", {"handle": handle})

    async def get_contest_list(self, gym: bool = False):
        """
        Returns information about upcoming and past contests.
        """
        return await self._make_request("contest.list", {"gym": str(gym).lower()})

    async def get_contest_standings(self, contest_id: int, from_index: int = 1, count: int = 5, show_unofficial: bool = False):
        """
        Returns the description of the contest and the requested part of the standings.
        """
        return await self._make_request("contest.standings", {
            "contestId": contest_id,
            "from": from_index,
            "count": count,
            "showUnofficial": str(show_unofficial).lower()
        })

    async def get_problems(self, tags: str = None, limit_kb: int = 500, start_index: int = 0):
        """
        Returns all problems from problemset. Problems can be filtered by tags.
        Results are paginated by size (limit_kb) to avoid large payloads.
        """
        params = {}
        if tags:
            params["tags"] = tags
        
        # Fetch all data since API doesn't support pagination for this endpoint
        full_data = await self._make_request("problemset.problems", params)
        
        problems = full_data.get("problems", [])
        statistics = full_data.get("problemStatistics", [])
        
        if start_index >= len(problems):
             return {
                 "problems": [], 
                 "problemStatistics": [], 
                 "next_start_index": None, 
                 "total_problems": len(problems)
             }

        current_size = 0
        limit_bytes = limit_kb * 1024
        
        sliced_problems = []
        sliced_stats = []
        
        next_index = None
        
        for i in range(start_index, len(problems)):
            prob = problems[i]
            # Ensure statistics align (assuming same order and length, which is standard for this API)
            stat = statistics[i] if i < len(statistics) else {}
            
            # Estimate size
            item_size = len(str(prob)) + len(str(stat))
            
            if current_size + item_size > limit_bytes and len(sliced_problems) > 0:
                next_index = i
                break
            
            sliced_problems.append(prob)
            sliced_stats.append(stat)
            current_size += item_size
            
        return {
            "problems": sliced_problems,
            "problemStatistics": sliced_stats,
            "next_start_index": next_index,
            "total_problems": len(problems)
        }

    async def get_user_blog_entries(self, handle: str):
        """
        Returns a list of all user's blog entries.
        """
        return await self._make_request("user.blogEntries", {"handle": handle})

if __name__ == "__main__":
    async def main():
        cf = CodeforcesAPI()
        try:
            print("Fetching user info for astral410...")
            info = await cf.get_user_info("astral410")
            print(info)
            
            print("\nFetching recent submissions...")
            submissions = await cf.get_user_status("astral410", count=5)
            print(f"Retrieved {len(submissions)} submissions")
            
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
