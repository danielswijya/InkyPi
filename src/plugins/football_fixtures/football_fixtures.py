import requests
import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

class FootballFixtures:
    def __init__(self, api_key=None, timezone='America/New_York'):
        # No API key needed for ESPN!
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/soccer"
        self.team_id = 363  # Chelsea FC on ESPN
        self.timezone = timezone
        
        # Leagues to check (in priority order)
        self.leagues = [
            ('eng.1', 'Premier League'),
            ('uefa.champions', 'Champions League'),
            ('eng.league_cup', 'Carabao Cup'),
            ('eng.fa', 'FA Cup'),
        ]
        
        # Caching for intelligent fetching
        self.last_fetch_time = None
        self.cached_fixture = None
        self.fetch_count_today = 0
        self.last_fetch_date = None
    
    def should_fetch(self):
        """Determine if we should fetch based on game day status."""
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if self.last_fetch_date != now.date():
            self.fetch_count_today = 0
            self.last_fetch_date = now.date()
        
        # If we have cached data, check if it's a game day
        if self.cached_fixture:
            is_game_day = self._is_game_day(self.cached_fixture)
            is_live = self.cached_fixture.get('is_live', False)
            
            if is_live or is_game_day:
                # Game day or live: fetch every 1 minute
                if self.last_fetch_time and (now - self.last_fetch_time) < timedelta(minutes=1):
                    return False
            else:
                # Non-game day: limit to 5 fetches per day
                if self.fetch_count_today >= 5:
                    logger.info(f"Reached daily fetch limit (5) for non-game day")
                    return False
                
                # Spread fetches throughout the day (roughly every 5 hours)
                if self.last_fetch_time and (now - self.last_fetch_time) < timedelta(hours=4, minutes=48):
                    return False
        
        return True
    
    def _is_game_day(self, fixture):
        """Check if the fixture is today."""
        try:
            status = fixture.get('status', '')
            
            # If it's live or recently finished, it's a game day
            if fixture.get('is_live'):
                return True
            
            if 'FT' in status or 'LIVE' in status:
                return True
            
            # Check if scheduled for today
            if fixture.get('match_date'):
                match_date = fixture['match_date']
                if isinstance(match_date, datetime):
                    return match_date.date() == datetime.now().date()
            
            return False
        except:
            return False
    
    def get_next_or_live_fixture(self):
        """Get the next fixture or current live match for Chelsea from ESPN."""
        try:
            # Check if we should fetch
            if not self.should_fetch():
                logger.info("Using cached fixture data")
                return self.cached_fixture
            
            # Update fetch tracking
            self.last_fetch_time = datetime.now()
            self.fetch_count_today += 1
            
            logger.info(f"Fetching fixture data (fetch #{self.fetch_count_today} today)")
            
            # Collect all fixtures from all leagues
            all_fixtures = []
            
            # Check each league for fixtures
            for league_id, league_name in self.leagues:
                logger.info(f"Checking {league_name} for Chelsea fixtures")
                
                url = f"{self.base_url}/{league_id}/teams/{self.team_id}"
                response = requests.get(url, timeout=10)
                
                logger.info(f"{league_name} response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.warning(f"Could not fetch {league_name} data: {response.status_code}")
                    continue
                
                data = response.json()
                
                # Check for next event
                next_event = data.get('team', {}).get('nextEvent')
                if next_event and len(next_event) > 0:
                    logger.info(f"Found next event in {league_name}")
                    fixture = self._format_fixture(next_event[0], league_name)
                    if fixture:
                        all_fixtures.append(fixture)
            
            # If we have fixtures, select the one nearest to now
            if all_fixtures:
                # Prioritize live matches first
                live_fixtures = [f for f in all_fixtures if f.get('is_live')]
                if live_fixtures:
                    self.cached_fixture = live_fixtures[0]
                    logger.info(f"Selected live fixture: {self.cached_fixture}")
                    return self.cached_fixture
                
                # Otherwise, select the match nearest to now by datetime
                now = datetime.now(pytz.timezone(self.timezone))
                fixtures_with_dates = [f for f in all_fixtures if f.get('match_date')]
                
                if fixtures_with_dates:
                    # Sort by absolute time difference from now
                    nearest_fixture = min(fixtures_with_dates, 
                                         key=lambda f: abs((f['match_date'] - now).total_seconds()))
                    self.cached_fixture = nearest_fixture
                    logger.info(f"Selected nearest fixture: {self.cached_fixture}")
                    return self.cached_fixture
                
                # Fallback to first fixture if no dates available
                self.cached_fixture = all_fixtures[0]
                return self.cached_fixture
            
            logger.warning("No fixtures found in any league")
            return self.cached_fixture  # Return last known fixture if available
            
        except Exception as e:
            logger.error(f"Error fetching fixtures from ESPN: {e}", exc_info=True)
            return self.cached_fixture
    
    def _format_fixture(self, event, league_name):
        """Format ESPN event data for display."""
        try:
            competitions = event.get('competitions', [])
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) < 2:
                return None
            
            # Find home and away teams
            home_team = None
            away_team = None
            
            for competitor in competitors:
                if competitor.get('homeAway') == 'home':
                    home_team = competitor
                else:
                    away_team = competitor
            
            if not home_team or not away_team:
                home_team = competitors[0]
                away_team = competitors[1]
            
            # Get status
            status_type = competition.get('status', {}).get('type', {}).get('name', 'STATUS_SCHEDULED')
            status_detail = competition.get('status', {}).get('type', {}).get('shortDetail', '')
            
            # Determine if live
            is_live = status_type in ['STATUS_IN_PROGRESS', 'STATUS_HALFTIME', 'STATUS_END_PERIOD']
            
            # Format status display
            match_date = None
            if is_live:
                clock = competition.get('status', {}).get('displayClock', '')
                period = competition.get('status', {}).get('period', 0)
                if period == 1:
                    status_display = f"{clock}' 1H"
                elif period == 2:
                    status_display = f"{clock}' 2H"
                elif status_type == 'STATUS_HALFTIME':
                    status_display = "HT"
                else:
                    status_display = status_detail or "LIVE"
            elif status_type == 'STATUS_FINAL':
                status_display = "FT"
            else:
                # Scheduled match - show date/time
                date_str = competition.get('date', '')
                if date_str:
                    try:
                        match_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        tz = pytz.timezone(self.timezone)
                        match_date = match_date.astimezone(tz)
                        status_display = match_date.strftime("%d %b %H:%M")
                    except:
                        status_display = status_detail or "Scheduled"
                else:
                    status_display = status_detail or "Scheduled"
            
            return {
                'home_team': {
                    'name': home_team.get('team', {}).get('displayName', 'Unknown'),
                    'logo': home_team.get('team', {}).get('logos', [{}])[0].get('href', '') if home_team.get('team', {}).get('logos') else ''
                },
                'away_team': {
                    'name': away_team.get('team', {}).get('displayName', 'Unknown'),
                    'logo': away_team.get('team', {}).get('logos', [{}])[0].get('href', '') if away_team.get('team', {}).get('logos') else ''
                },
                'score': f"{home_team.get('score', '0')} - {away_team.get('score', '0')}",
                'status': status_display,
                'is_live': is_live,
                'league': league_name,
                'match_date': match_date
            }
            
        except Exception as e:
            logger.error(f"Error formatting ESPN fixture: {e}", exc_info=True)
            return None
