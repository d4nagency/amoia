import pandas as pd
import os
import re
from fuzzywuzzy import fuzz
import xlsxwriter
import matplotlib.pyplot as plt
from datetime import datetime

def clean_show_name(name):
    """Clean show names for better comparison"""
    if pd.isna(name):
        return ""
    
    # Convert to lowercase
    name = str(name).lower().strip()
    
    # Remove "(comm/promo)" prefix
    name = re.sub(r'^\(comm/promo\)\s*', '', name)
    
    # Remove special characters but keep spaces
    name = re.sub(r'[^\w\s]', '', name)
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    return name

def clean_song_title(title):
    """Clean song titles for better comparison"""
    if pd.isna(title):
        return ""
    
    # Convert to lowercase
    title = str(title).lower().strip()
    
    # Remove special characters but keep spaces
    title = re.sub(r'[^\w\s]', '', title)
    
    # Remove extra whitespace
    title = ' '.join(title.split())
    
    return title

def find_similar_shows(show_name, show_list, threshold=85):
    """Find similar show names using fuzzy matching"""
    matches = []
    for other_show in show_list:
        ratio = fuzz.ratio(show_name, other_show)
        if ratio >= threshold:
            matches.append((other_show, ratio))
    return sorted(matches, key=lambda x: x[1], reverse=True)

def fuzzy_match(a, b):
    return fuzz.ratio(a, b) >= 80

def create_excel_report(ascap_df, bmi_df, matches, episode_matches, only_in_ascap, only_in_bmi, songs_only_in_ascap, songs_only_in_bmi, output_file):
    """Create a detailed Excel report with multiple sheets and charts"""
    workbook = xlsxwriter.Workbook(output_file)

    # Create formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'bg_color': '#D3D3D3',
        'border': 1
    })
    
    money_format = workbook.add_format({'num_format': '$#,##0.00'})
    percent_format = workbook.add_format({'num_format': '0.00%'})

    # Show Episodes Analysis sheet
    show_episodes_sheet = workbook.add_worksheet('Show Episodes Analysis')
    headers = ['Show Name', 'Total Songs in ASCAP', 'Total Songs in BMI', 
              'Songs Missing from ASCAP', 'Songs Missing from BMI', 'BMI Amount', 'ASCAP Amount', 'Difference']
    show_episodes_sheet.write_row(0, 0, headers, header_format)
    
    current_row = 1
    for show, match_info in matches.items():
        if show in episode_matches:
            ascap_episodes = episode_matches[show]['ascap_episodes']
            bmi_episodes = episode_matches[show]['bmi_episodes']
            
            # Create dictionaries for faster lookup
            ascap_dict = {}
            for ep in ascap_episodes:
                key = (ep['Program Name'], ep['Work Title'])
                ascap_dict[key] = float(ep['Dollars'])

            bmi_dict = {}
            for ep in bmi_episodes:
                key = (ep['EPISODE NAME'], ep['TITLE NAME'])
                bmi_dict[key] = float(ep['ROYALTY AMOUNT'])
            
            # Calculate totals
            bmi_amount = sum(bmi_dict.values())
            ascap_amount = sum(ascap_dict.values())
            difference = abs(bmi_amount - ascap_amount)
            
            # Write show info
            show_episodes_sheet.write(current_row, 0, show)
            show_episodes_sheet.write(current_row, 1, len(ascap_dict))
            show_episodes_sheet.write(current_row, 2, len(bmi_dict))
            
            # Get all songs from both sources
            bmi_songs = sorted([song for _, song in bmi_dict.keys()])
            ascap_songs = sorted([song for _, song in ascap_dict.keys()])
            
            # Write songs in columns
            max_songs = max(len(bmi_songs), len(ascap_songs))
            for i in range(max_songs):
                if i < len(bmi_songs):
                    show_episodes_sheet.write(current_row + i, 3, bmi_songs[i])
                if i < len(ascap_songs):
                    show_episodes_sheet.write(current_row + i, 4, ascap_songs[i])
            
            # Write amounts
            show_episodes_sheet.write(current_row, 5, bmi_amount, money_format)
            show_episodes_sheet.write(current_row, 6, ascap_amount, money_format)
            show_episodes_sheet.write(current_row, 7, difference, money_format)
            
            # Move to next show's starting row
            current_row += max(max_songs, 1) + 1  # Add 1 for spacing between shows
    
    # Adjust column widths
    show_episodes_sheet.set_column(0, 0, 30)  # Show Name
    show_episodes_sheet.set_column(1, 2, 15)  # Total Songs
    show_episodes_sheet.set_column(3, 4, 40)  # Songs Lists
    show_episodes_sheet.set_column(5, 7, 15)  # Amounts
    
    # Set row height to accommodate multiple lines
    show_episodes_sheet.set_default_row(60)
    
    # Enable text wrapping for songs columns
    wrap_format = workbook.add_format({'text_wrap': True})
    show_episodes_sheet.set_column(3, 4, 40, wrap_format)

    # Summary sheet
    summary_data = []
    total_ascap = 0
    total_bmi = 0
    
    for show, match_info in matches.items():
        ascap_amount = match_info['ascap_amount']
        bmi_amount = match_info['bmi_amount']
        diff = abs(ascap_amount - bmi_amount)
        diff_percent = diff / max(ascap_amount, bmi_amount) if max(ascap_amount, bmi_amount) > 0 else 0
        
        total_ascap += ascap_amount
        total_bmi += bmi_amount
        
        summary_data.append({
            'Show Name': show,
            'ASCAP Amount': ascap_amount,
            'BMI Amount': bmi_amount,
            'Difference': diff,
            'Difference %': diff_percent,
            'Match Quality': match_info['match_quality']
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('Difference', ascending=False)
    
    # Write summary sheet
    summary_sheet = workbook.add_worksheet('Summary')
    summary_sheet.write_row(0, 0, summary_df.columns, header_format)
    
    for i, row in enumerate(summary_df.values, 1):
        summary_sheet.write(i, 0, str(row[0]))  # Show Name
        summary_sheet.write(i, 1, float(row[1]), money_format)  # ASCAP Amount
        summary_sheet.write(i, 2, float(row[2]), money_format)  # BMI Amount
        summary_sheet.write(i, 3, float(row[3]), money_format)  # Difference
        summary_sheet.write(i, 4, float(row[4]), percent_format)  # Difference %
        summary_sheet.write(i, 5, float(row[5]))  # Match Quality

    # Episode breakdown sheet
    episode_sheet = workbook.add_worksheet('Episode Breakdown')
    current_row = 0
    
    episode_headers = ['Show Name', 'Episode Title', 'Song Title', 'Network', 'ASCAP Amount', 'BMI Amount', 'Difference']
    episode_sheet.write_row(current_row, 0, episode_headers, header_format)
    current_row += 1
    
    for show, episodes in episode_matches.items():
        ascap_episodes = episodes['ascap_episodes']
        bmi_episodes = episodes['bmi_episodes']
        
        # Create a mapping of episode+song combinations
        episode_song_map = {}
        
        # Process ASCAP episodes
        for ep in ascap_episodes:
            key = (ep['Program Name'], ep['Work Title'])
            network = str(ep['Network Service']) if pd.notna(ep['Network Service']) else ''
            if key not in episode_song_map:
                episode_song_map[key] = {'ascap': float(ep['Dollars']), 'bmi': 0.0, 'network': network}
            else:
                episode_song_map[key]['ascap'] = float(ep['Dollars'])
                
        # Process BMI episodes
        for ep in bmi_episodes:
            key = (ep['EPISODE NAME'], ep['TITLE NAME'])
            network = str(ep['PERF SOURCE']) if pd.notna(ep['PERF SOURCE']) else ''
            if key not in episode_song_map:
                episode_song_map[key] = {'ascap': 0.0, 'bmi': float(ep['ROYALTY AMOUNT']), 'network': network}
            else:
                episode_song_map[key]['bmi'] = float(ep['ROYALTY AMOUNT'])
        
        # Write episode data
        for (episode, song), amounts in episode_song_map.items():
            episode_sheet.write(current_row, 0, str(show))
            episode_sheet.write(current_row, 1, str(episode) if pd.notna(episode) else '')
            episode_sheet.write(current_row, 2, str(song) if pd.notna(song) else '')
            episode_sheet.write(current_row, 3, str(amounts['network']))
            episode_sheet.write(current_row, 4, amounts['ascap'], money_format)
            episode_sheet.write(current_row, 5, amounts['bmi'], money_format)
            diff = abs(amounts['ascap'] - amounts['bmi'])
            episode_sheet.write(current_row, 6, diff, money_format)
            current_row += 1
        
        # Add a blank row between shows
        current_row += 1

    # Songs only in ASCAP sheet
    ascap_only_sheet = workbook.add_worksheet('Songs Only in ASCAP')
    ascap_headers = ['Show Name', 'Episode', 'Song Title', 'Network', 'Amount']
    ascap_only_sheet.write_row(0, 0, ascap_headers, header_format)
    
    for i, song in enumerate(songs_only_in_ascap, 1):
        ascap_only_sheet.write(i, 0, str(song['show']) if pd.notna(song['show']) else '')
        ascap_only_sheet.write(i, 1, str(song['episode']) if pd.notna(song['episode']) else '')
        ascap_only_sheet.write(i, 2, str(song['song']) if pd.notna(song['song']) else '')
        ascap_only_sheet.write(i, 3, str(song['network']) if pd.notna(song['network']) else '')
        ascap_only_sheet.write(i, 4, float(song['amount']), money_format)

    # Songs only in BMI sheet
    bmi_only_sheet = workbook.add_worksheet('Songs Only in BMI')
    bmi_headers = ['Show Name', 'Episode', 'Song Title', 'Network', 'Amount']
    bmi_only_sheet.write_row(0, 0, bmi_headers, header_format)
    
    for i, song in enumerate(songs_only_in_bmi, 1):
        bmi_only_sheet.write(i, 0, str(song['show']) if pd.notna(song['show']) else '')
        bmi_only_sheet.write(i, 1, str(song['episode']) if pd.notna(song['episode']) else '')
        bmi_only_sheet.write(i, 2, str(song['song']) if pd.notna(song['song']) else '')
        bmi_only_sheet.write(i, 3, str(song['network']) if pd.notna(song['network']) else '')
        bmi_only_sheet.write(i, 4, float(song['amount']), money_format)

    # Adjust column widths
    for sheet in [summary_sheet, episode_sheet, ascap_only_sheet, bmi_only_sheet]:
        sheet.set_column(0, 0, 40)  # Show Name
        sheet.set_column(1, 1, 30)  # Episode/Network
        sheet.set_column(2, 2, 40)  # Song Title
        sheet.set_column(3, 6, 15)  # Amounts and other columns

    # Create summary charts
    chart_sheet = workbook.add_worksheet('Charts')
    
    # Total earnings comparison chart
    total_chart = workbook.add_chart({'type': 'column'})
    total_chart.add_series({
        'name': 'ASCAP',
        'values': '=Summary!$B$2:$B$' + str(len(summary_df) + 1),
        'categories': '=Summary!$A$2:$A$' + str(len(summary_df) + 1),
    })
    total_chart.add_series({
        'name': 'BMI',
        'values': '=Summary!$C$2:$C$' + str(len(summary_df) + 1),
    })
    total_chart.set_title({'name': 'Earnings Comparison by Show'})
    total_chart.set_x_axis({'name': 'Show'})
    total_chart.set_y_axis({'name': 'Amount ($)'})
    chart_sheet.insert_chart('A1', total_chart, {'x_scale': 2, 'y_scale': 2})

    workbook.close()
    
    print(f"Excel report created successfully: {output_file}")
    return output_file

def compare_earnings(ascap_path, bmi_path):
    """
    Compare earnings data between ASCAP and BMI files with enhanced matching and reporting
    """
    try:
        # Read CSVs with low_memory=False to handle mixed types
        ascap_df = pd.read_csv(ascap_path, low_memory=False)
        bmi_df = pd.read_csv(bmi_path, low_memory=False)
    except Exception as e:
        print(f"Error reading CSV files: {str(e)}")
        return

    # Clean and normalize show names and song titles
    ascap_df['clean_name'] = ascap_df['Series or Film/Attraction'].apply(clean_show_name)
    bmi_df['clean_name'] = bmi_df['SHOW NAME'].apply(clean_show_name)
    
    ascap_df['clean_song_title'] = ascap_df['Work Title'].apply(clean_song_title)
    bmi_df['clean_song_title'] = bmi_df['TITLE NAME'].apply(clean_song_title)

    # Create sets of unique shows and songs
    ascap_shows = set(ascap_df['clean_name'].dropna())
    bmi_shows = set(bmi_df['clean_name'].dropna())
    
    # Initialize matching results
    matches = {}
    episode_matches = {}
    only_in_ascap = set()
    only_in_bmi = set()
    songs_only_in_ascap = []
    songs_only_in_bmi = []

    # First, find exact matches
    exact_matches = ascap_shows.intersection(bmi_shows)
    for show in exact_matches:
        ascap_rows = ascap_df[ascap_df['clean_name'] == show]
        bmi_rows = bmi_df[bmi_df['clean_name'] == show]
        
        ascap_amount = ascap_rows['Dollars'].sum()
        bmi_amount = bmi_rows['ROYALTY AMOUNT'].sum()
        
        # Group by episode
        ascap_episodes = ascap_rows.groupby(['Program Name', 'Work Title']).agg({
            'Dollars': 'sum',
            'Network Service': 'first'
        }).reset_index()
        
        bmi_episodes = bmi_rows.groupby(['EPISODE NAME', 'TITLE NAME']).agg({
            'ROYALTY AMOUNT': 'sum',
            'PERF SOURCE': 'first'  # Using PERF SOURCE as network
        }).reset_index()
        
        # Store episode-level data
        episode_matches[show] = {
            'ascap_episodes': ascap_episodes.to_dict('records'),
            'bmi_episodes': bmi_episodes.to_dict('records')
        }
        
        # Store show-level data
        matches[show] = {
            'ascap_amount': ascap_amount,
            'bmi_amount': bmi_amount,
            'match_quality': 100
        }

    # Then, try fuzzy matching for remaining shows
    remaining_ascap = ascap_shows - exact_matches
    remaining_bmi = bmi_shows - exact_matches

    for ascap_show in remaining_ascap:
        similar_shows = find_similar_shows(ascap_show, remaining_bmi)
        if similar_shows:
            best_match, match_quality = similar_shows[0]
            if match_quality >= 85:  # Only consider high-quality matches
                ascap_rows = ascap_df[ascap_df['clean_name'] == ascap_show]
                bmi_rows = bmi_df[bmi_df['clean_name'] == best_match]
                
                ascap_amount = ascap_rows['Dollars'].sum()
                bmi_amount = bmi_rows['ROYALTY AMOUNT'].sum()
                
                # Group by episode
                ascap_episodes = ascap_rows.groupby(['Program Name', 'Work Title']).agg({
                    'Dollars': 'sum',
                    'Network Service': 'first'
                }).reset_index()
                
                bmi_episodes = bmi_rows.groupby(['EPISODE NAME', 'TITLE NAME']).agg({
                    'ROYALTY AMOUNT': 'sum',
                    'PERF SOURCE': 'first'  # Using PERF SOURCE as network
                }).reset_index()
                
                # Store episode-level data
                episode_matches[ascap_show] = {
                    'ascap_episodes': ascap_episodes.to_dict('records'),
                    'bmi_episodes': bmi_episodes.to_dict('records')
                }
                
                matches[ascap_show] = {
                    'ascap_amount': ascap_amount,
                    'bmi_amount': bmi_amount,
                    'match_quality': match_quality
                }
                remaining_bmi.remove(best_match)
            else:
                only_in_ascap.add(ascap_show)
        else:
            only_in_ascap.add(ascap_show)

    # Add remaining BMI shows to unmatched
    only_in_bmi.update(remaining_bmi)

    # Get detailed information for songs only in ASCAP
    for show in only_in_ascap:
        ascap_rows = ascap_df[ascap_df['clean_name'] == show]
        for _, row in ascap_rows.iterrows():
            songs_only_in_ascap.append({
                'show': show,
                'episode': row['Program Name'],
                'song': row['Work Title'],
                'network': row['Network Service'],
                'amount': row['Dollars']
            })

    # Get detailed information for songs only in BMI
    for show in only_in_bmi:
        bmi_rows = bmi_df[bmi_df['clean_name'] == show]
        for _, row in bmi_rows.iterrows():
            songs_only_in_bmi.append({
                'show': show,
                'episode': row['EPISODE NAME'],
                'song': row['TITLE NAME'],
                'network': row['PERF SOURCE'],
                'amount': row['ROYALTY AMOUNT']
            })

    # Generate Excel report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = f'earnings_comparison_report_{timestamp}.xlsx'
    create_excel_report(ascap_df, bmi_df, matches, episode_matches, only_in_ascap, only_in_bmi, songs_only_in_ascap, songs_only_in_bmi, excel_file)
    
    print(f"\nAnalysis complete! Excel report generated: {excel_file}")
    print(f"Total shows analyzed: {len(matches)}")
    print(f"Shows only in ASCAP: {len(only_in_ascap)}")
    print(f"Shows only in BMI: {len(only_in_bmi)}")
    print(f"Songs only in ASCAP: {len(songs_only_in_ascap)}")
    print(f"Songs only in BMI: {len(songs_only_in_bmi)}")
    
    return excel_file  # Return the path to the generated Excel file

if __name__ == '__main__':
    # Files to compare
    ascap_file = "/Users/test/Desktop/PROJECTS/amoia/ASCAP 4TH 2023.csv"
    bmi_file = "/Users/test/Desktop/PROJECTS/amoia/BMI 4TH 2023.csv"

    if not os.path.exists(ascap_file) or not os.path.exists(bmi_file):
        print("Error: One or both CSV files not found!")
    else:
        compare_earnings(ascap_file, bmi_file)
