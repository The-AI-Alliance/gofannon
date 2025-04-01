import os
import csv
import json
import sys
from datetime import datetime, timedelta
from github import Github, GithubException
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.api_core.exceptions import GoogleAPICallError

def get_github_historical_stats(github_token, repo_name):
    """Get historical GitHub stats (views, clones, stars, forks)"""
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)

        # Get traffic data (last 14 days)
        traffic = repo.get_views_traffic(per="day")
        clones = repo.get_clones_traffic(per="day")

        # Get historical stars (approximate)
        stars_timeline = []
        stargazers = repo.get_stargazers_with_dates()
        for sg in stargazers:
            stars_timeline.append(sg.starred_at.date())

            # Get historical forks (approximate)
        forks = list(repo.get_forks())

        # Aggregate daily stats
        historical_data = {}
        for day in range(14, 0, -1):
            date = (datetime.utcnow() - timedelta(days=day)).date()
            date_str = date.strftime('%Y-%m-%d')

            # Views
            day_views = sum(view.count for view in traffic['views']
                            if view.timestamp.date() == date)
            day_uniques = sum(view.uniques for view in traffic['views']
                              if view.timestamp.date() == date)

            # Clones
            day_clones = sum(clone.count for clone in clones['clones']
                             if clone.timestamp.date() == date)
            day_cloners = sum(clone.uniques for clone in clones['clones']
                              if clone.timestamp.date() == date)

            # Stars (count up to this date)
            day_stars = sum(1 for starred_at in stars_timeline
                            if starred_at <= date)

            # Forks (count up to this date)
            day_forks = sum(1 for fork in forks
                            if fork.created_at.date() <= date)

            historical_data[date_str] = {
                'github_views': day_views,
                'github_unique_visitors': day_uniques,
                'github_clones': day_clones,
                'github_unique_cloners': day_cloners,
                'github_stars': day_stars,
                'github_forks': day_forks,
                'ga_active_users': 'N/A',
                'ga_page_views': 'N/A',
                'ga_sessions': 'N/A'
            }

        return historical_data
    except GithubException as e:
        print(f"GitHub API error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error getting GitHub historical stats: {e}", file=sys.stderr)
        return None

def get_github_daily_stats(github_token, repo_name):
    """Get today's GitHub stats"""
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)

        # Get traffic data for the last day
        traffic = repo.get_views_traffic(per="day")
        clones = repo.get_clones_traffic(per="day")

        return {
            'github_views': sum(view.count for view in traffic['views']),
            'github_unique_visitors': sum(view.uniques for view in traffic['views']),
            'github_clones': sum(clone.count for clone in clones['clones']),
            'github_unique_cloners': sum(clone.uniques for clone in clones['clones']),
            'github_stars': repo.stargazers_count,
            'github_forks': repo.forks_count
        }
    except GithubException as e:
        print(f"GitHub API error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error getting GitHub stats: {e}", file=sys.stderr)
        return None

def get_google_analytics_stats(property_id, credentials_json, date_str):
    """Get GA stats for a specific date"""
    try:
        credentials = json.loads(credentials_json)
        client = BetaAnalyticsDataClient.from_service_account_info(credentials)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="sessions")
            ],
        )

        response = client.run_report(request)

        if len(response.rows) > 0:
            row = response.rows[0]
            return {
                'ga_active_users': row.metric_values[0].value,
                'ga_page_views': row.metric_values[1].value,
                'ga_sessions': row.metric_values[2].value
            }
        return {
            'ga_active_users': 0,
            'ga_page_views': 0,
            'ga_sessions': 0
        }
    except GoogleAPICallError as e:
        print(f"Google Analytics API error for {date_str}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Invalid GA_CREDENTIALS JSON format", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error getting GA stats for {date_str}: {e}", file=sys.stderr)
        return None

def initialize_csv(file_path):
    """Create CSV with historical data"""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    ga_property_id = os.getenv('GA_PROPERTY_ID')
    ga_credentials = os.getenv('GA_CREDENTIALS')

    if not github_token or not repo_name:
        print("Missing GitHub credentials", file=sys.stderr)
        return False

        # Get GitHub historical data
    historical_data = get_github_historical_stats(github_token, repo_name)
    if historical_data is None:
        return False

        # Add GA data if available
    if ga_property_id and ga_credentials:
        for date_str, data in historical_data.items():
            ga_stats = get_google_analytics_stats(ga_property_id, ga_credentials, date_str)
            if ga_stats:
                data.update(ga_stats)

                # Write all data to CSV
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', newline='') as f:
            if not historical_data:
                return False

                # Get fieldnames from first entry
            sample_data = next(iter(historical_data.values()))
            fieldnames = ['date'] + list(sample_data.keys())

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for date_str, data in historical_data.items():
                row = {'date': date_str, **data}
                writer.writerow(row)

        return True
    except IOError as e:
        print(f"Error writing historical CSV: {e}", file=sys.stderr)
        return False

def append_daily_stats(file_path):
    """Append today's stats to existing CSV"""
    today = datetime.utcnow().strftime('%Y-%m-%d')

    # Get GitHub stats
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    github_stats = get_github_daily_stats(github_token, repo_name)
    if github_stats is None:
        return False

        # Get Google Analytics stats
    ga_property_id = os.getenv('GA_PROPERTY_ID')
    ga_credentials = os.getenv('GA_CREDENTIALS')

    if ga_property_id and ga_credentials:
        ga_stats = get_google_analytics_stats(ga_property_id, ga_credentials, today)
        if ga_stats is None:
            ga_stats = {
                'ga_active_users': 'ERROR',
                'ga_page_views': 'ERROR',
                'ga_sessions': 'ERROR'
            }
    else:
        ga_stats = {
            'ga_active_users': 'N/A',
            'ga_page_views': 'N/A',
            'ga_sessions': 'N/A'
        }

        # Combine all stats
    all_stats = {**github_stats, **ga_stats}

    # Write to CSV
    try:
        with open(file_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['date'] + list(all_stats.keys()))
            writer.writerow({'date': today, **all_stats})
        return True
    except IOError as e:
        print(f"Error appending to CSV: {e}", file=sys.stderr)
        return False

def main():
    file_path = 'website/community/stats.csv'

    if not os.path.exists(file_path):
        print("Initializing new stats CSV with historical data...")
        if not initialize_csv(file_path):
            sys.exit(1)
    else:
        if not append_daily_stats(file_path):
            sys.exit(1)

if __name__ == "__main__":
    main()  