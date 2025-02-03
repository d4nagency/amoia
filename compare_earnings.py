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

def find_similar_shows(show_name, show_list, threshold=85):
    """Find similar show names using fuzzy matching"""
    matches = []
    for other_show in show_list:
        ratio = fuzz.ratio(show_name, other_show)
        if ratio >= threshold:
            matches.append((other_show, ratio))
    return sorted(matches, key=lambda x: x[1], reverse=True)

def create_excel_report(ascap_df, bmi_df, matches, only_in_ascap, only_in_bmi, output_file):
    """Create a detailed Excel report with multiple sheets and charts"""
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook = writer.book

    # Create formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D3D3D3',
        'border': 1
    })
    
    money_format = workbook.add_format({'num_format': '$#,##0.00'})
    percent_format = workbook.add_format({'num_format': '0.00%'})
    red_format = workbook.add_format({'bg_color': '#FFB6C1'})
    green_format = workbook.add_format({'bg_color': '#90EE90'})

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
            'Match Quality': match_info.get('match_quality', 100)
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('Difference', ascending=False)
    
    # Write summary sheet
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    summary_sheet = writer.sheets['Summary']
    
    # Format summary sheet
    for col_num, value in enumerate(summary_df.columns.values):
        summary_sheet.write(0, col_num, value, header_format)
        
    # Apply conditional formatting
    summary_sheet.conditional_format(1, 4, len(summary_df), 4,
                                   {'type': '3_color_scale',
                                    'min_color': "#90EE90",
                                    'mid_color': "#FFFF00",
                                    'max_color': "#FFB6C1"})

    # Create charts
    chart1 = workbook.add_chart({'type': 'column'})
    chart1.add_series({
        'name': 'ASCAP',
        'values': f'=Summary!$B$2:$B${len(summary_df)+1}',
        'categories': f'=Summary!$A$2:$A${len(summary_df)+1}'
    })
    chart1.add_series({
        'name': 'BMI',
        'values': f'=Summary!$C$2:$C${len(summary_df)+1}'
    })
    chart1.set_title({'name': 'ASCAP vs BMI Earnings Comparison'})
    chart1.set_x_axis({'name': 'Shows'})
    chart1.set_y_axis({'name': 'Earnings ($)'})
    
    # Add chart to new sheet
    chart_sheet = workbook.add_worksheet('Charts')
    chart_sheet.insert_chart('A1', chart1, {'x_scale': 2, 'y_scale': 2})

    # Unmatched shows sheet
    unmatched_data = {
        'Only in ASCAP': list(only_in_ascap) + [''] * (len(only_in_bmi) - len(only_in_ascap)),
        'Only in BMI': list(only_in_bmi) + [''] * (len(only_in_ascap) - len(only_in_bmi))
    }
    unmatched_df = pd.DataFrame(unmatched_data)
    unmatched_df.to_excel(writer, sheet_name='Unmatched Shows', index=False)
    
    # Format columns
    for sheet in writer.sheets.values():
        sheet.set_column('A:A', 40)
        sheet.set_column('B:E', 15)

    writer.close()

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

    # Clean and normalize show names
    ascap_df['clean_name'] = ascap_df['Series or Film/Attraction'].apply(clean_show_name)
    bmi_df['clean_name'] = bmi_df['SHOW NAME'].apply(clean_show_name)

    # Create sets of unique shows
    ascap_shows = set(ascap_df['clean_name'].dropna())
    bmi_shows = set(bmi_df['clean_name'].dropna())

    # Initialize matching results
    matches = {}
    only_in_ascap = set()
    only_in_bmi = set()

    # First, find exact matches
    exact_matches = ascap_shows.intersection(bmi_shows)
    for show in exact_matches:
        ascap_amount = ascap_df[ascap_df['clean_name'] == show]['Dollars'].sum()
        bmi_amount = bmi_df[bmi_df['clean_name'] == show]['ROYALTY AMOUNT'].sum()
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
                ascap_amount = ascap_df[ascap_df['clean_name'] == ascap_show]['Dollars'].sum()
                bmi_amount = bmi_df[bmi_df['clean_name'] == best_match]['ROYALTY AMOUNT'].sum()
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

    # Generate Excel report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = f'earnings_comparison_report_{timestamp}.xlsx'
    create_excel_report(ascap_df, bmi_df, matches, only_in_ascap, only_in_bmi, excel_file)
    
    print(f"\nAnalysis complete! Excel report generated: {excel_file}")
    print(f"Total shows analyzed: {len(matches)}")
    print(f"Shows only in ASCAP: {len(only_in_ascap)}")
    print(f"Shows only in BMI: {len(only_in_bmi)}")
    
    return excel_file  # Return the path to the generated Excel file

# Files to compare
ascap_file = "/Users/test/Desktop/PROJECTS/amoia/ASCAP 4TH 2023.csv"
bmi_file = "/Users/test/Desktop/PROJECTS/amoia/BMI 4TH 2023.csv"

if not os.path.exists(ascap_file) or not os.path.exists(bmi_file):
    print("Error: One or both CSV files not found!")
else:
    compare_earnings(ascap_file, bmi_file)
