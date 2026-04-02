#!/usr/bin/env python3
"""
Script to download LAS files covering a polygon area in EPSG:3059 coordinate system.
Each LAS file covers 1 square kilometer.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Set, Tuple, Optional
from shapely import wkt
from shapely.geometry import Polygon, box


def calculate_las_filename(easting: float, northing: float) -> Tuple[str, str]:
    """
    Calculate LAS filename and directory for given coordinates.
    
    Args:
        easting: Easting coordinate in EPSG:3059
        northing: Northing coordinate in EPSG:3059
    
    Returns:
        Tuple of (directory_name, filename)
    
    Note: In the formulas, X=northing and Y=easting (reversed from typical convention)
    """
    # In the formulas: X is northing, Y is easting
    X = northing
    Y = easting
    
    # Calculate components
    A = int(X / 100000) + 1
    B = int(Y / 100000) - 2
    C = int((Y % 100000) / 50000) + 1 + int((X % 100000) / 50000) * 2
    D = int((Y % 50000) / 25000) + 1 + int((X % 50000) / 25000) * 2
    E = int((X % 25000) / 5000) + 1
    F = int((Y % 25000) / 5000) + 1
    G = int((X % 5000) / 1000) + 1
    H = int((Y % 5000) / 1000) + 1
    
    # Format directory and filename
    directory = f"{A}{B}{C}{D}"
    filename = f"{A}{B}{C}{D}-{E}{F}-{G}{H}.las"
    
    return directory, filename


def get_tile_polygon(easting: float, northing: float) -> Polygon:
    """
    Get the 1km x 1km tile polygon for given coordinates.
    
    Args:
        easting: Easting coordinate in EPSG:3059
        northing: Northing coordinate in EPSG:3059
    
    Returns:
        Polygon representing the 1km tile
    """
    # Round down to nearest 1000m (1km)
    tile_easting = int(easting / 1000) * 1000
    tile_northing = int(northing / 1000) * 1000
    
    return box(tile_easting, tile_northing, tile_easting + 1000, tile_northing + 1000)


def get_tiles_for_polygon(polygon: Polygon) -> Set[Tuple[str, str, str]]:
    """
    Get all LAS tiles that intersect with the given polygon.
    
    Args:
        polygon: Shapely polygon in EPSG:3059 coordinates
    
    Returns:
        Set of tuples (directory, filename, url)
    """
    base_url = "https://s3.storage.pub.lvdc.gov.lv/lgia-opendata/las/"
    tiles = set()
    
    # Get bounding box (minx=min_easting, miny=min_northing, etc.)
    min_easting, min_northing, max_easting, max_northing = polygon.bounds
    
    # Round to nearest 1km grid
    min_tile_easting = int(min_easting / 1000) * 1000
    min_tile_northing = int(min_northing / 1000) * 1000
    max_tile_easting = int(max_easting / 1000) * 1000 + 1000
    max_tile_northing = int(max_northing / 1000) * 1000 + 1000
    
    # Iterate through all potential tiles
    northing = min_tile_northing
    while northing < max_tile_northing:
        easting = min_tile_easting
        while easting < max_tile_easting:
            # Create tile polygon
            tile_poly = get_tile_polygon(easting, northing)
            
            # Check if tile intersects with input polygon
            if tile_poly.intersects(polygon):
                # Use center of tile for filename calculation
                center_easting = easting + 500
                center_northing = northing + 500
                
                directory, filename = calculate_las_filename(center_easting, center_northing)
                url = f"{base_url}{directory}/{filename}"
                tiles.add((directory, filename, url))
            
            easting += 1000
        northing += 1000
    
    return tiles


def download_file(url: str, output_path: Path, curl_path: str = "curl.exe") -> bool:
    """
    Download a file from URL to output_path using curl if it doesn't already exist.
    
    Args:
        url: URL to download from
        output_path: Path to save file to
        curl_path: Path to curl executable (default: "curl.exe")
    
    Returns:
        True if file was downloaded, False if it already existed or download failed
    """
    if output_path.exists():
        print(f"File already exists: {output_path}")
        return False
    
    print(f"Downloading: {url}")
    
    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build curl command
    # -L: follow redirects
    # -f: fail silently on server errors
    # -o: output file
    # Curl will show its default progress output
    
    curl_cmd = [curl_path, "-L", "-f", "-o", str(output_path), url]
    
    try:
        # Run curl with default output (progress will be shown automatically)
        result = subprocess.run(
            curl_cmd,
            check=True
        )
        
        print(f"Downloaded: {output_path}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {url}: curl returned exit code {e.returncode}")
        # Clean up partial download
        if output_path.exists():
            output_path.unlink()
        return False
    except FileNotFoundError:
        print(f"Error: curl not found at '{curl_path}'. Please check the path or install curl.")
        return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        # Clean up partial download
        if output_path.exists():
            output_path.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download LAS files covering a polygon area in EPSG:3059'
    )
    parser.add_argument(
        'polygon',
        type=str,
        help='Polygon in WKT format, e.g., "POLYGON((x1 y1, x2 y2, ...))"'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='./las_files',
        help='Output directory for downloaded files (default: ./las_files)'
    )
    parser.add_argument(
        '--list-only',
        action='store_true',
        help='Only list URLs without downloading'
    )
    parser.add_argument(
        '--curl-path',
        type=str,
        default='curl.exe',
        help='Path to curl executable (default: curl.exe)'
    )
    
    args = parser.parse_args()
    
    # Parse polygon
    try:
        polygon = wkt.loads(args.polygon)
        if not isinstance(polygon, Polygon):
            print("Error: Input must be a POLYGON", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error parsing WKT polygon: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get tiles
    tiles = get_tiles_for_polygon(polygon)
    
    if not tiles:
        print("No tiles found for the given polygon")
        return
    
    print(f"Found {len(tiles)} tiles covering the polygon")
    print()
    
    if args.list_only:
        print("URLs:")
        for directory, filename, url in sorted(tiles):
            print(url)
    else:
        # Download files
        output_dir = Path(args.output_dir)
        downloaded = 0
        skipped = 0
        failed = 0
        
        tiles_list = sorted(tiles)
        
        for i, (directory, filename, url) in enumerate(tiles_list, 1):
            print(f"\n[{i}/{len(tiles_list)}] {filename}")
            
            output_path = output_dir / filename
            result = download_file(url, output_path, curl_path=args.curl_path)
            
            if result:
                downloaded += 1
            elif output_path.exists():
                skipped += 1
            else:
                failed += 1
        
        print()
        print(f"Summary:")
        print(f"  Downloaded: {downloaded}")
        print(f"  Skipped (already exist): {skipped}")
        print(f"  Failed: {failed}")


if __name__ == '__main__':
    main()
