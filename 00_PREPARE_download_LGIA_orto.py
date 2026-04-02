#!/usr/bin/env python3
"""
Script to download georeferenced TIF images and world files (.tfw) covering a polygon area 
in EPSG:3059 coordinate system. Each TIF tile covers 2.5 square kilometers.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import Set, Tuple
from shapely import wkt
from shapely.geometry import Polygon, box


def calculate_tif_filename(easting: float, northing: float) -> Tuple[str, str]:
    """
    Calculate TIF filename and directory for given coordinates.
    
    Args:
        easting: Easting coordinate in EPSG:3059
        northing: Northing coordinate in EPSG:3059
    
    Returns:
        Tuple of (directory_name, filename_base)
    
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
    G = int((Y % 5000) / 2500) + 1 + int((X % 5000) / 2500) * 2
    
    # Format directory and filename base
    directory = f"{A}{B}{C}{D}"
    filename_base = f"{A}{B}{C}{D}-{E}{F}_{G}"
    
    return directory, filename_base


def get_tile_polygon(easting: float, northing: float) -> Polygon:
    """
    Get the 2.5km x 2.5km tile polygon for given coordinates.
    
    Args:
        easting: Easting coordinate in EPSG:3059
        northing: Northing coordinate in EPSG:3059
    
    Returns:
        Polygon representing the 2.5km tile
    """
    # Round down to nearest 2500m (2.5km)
    tile_easting = int(easting / 2500) * 2500
    tile_northing = int(northing / 2500) * 2500
    
    return box(tile_easting, tile_northing, tile_easting + 2500, tile_northing + 2500)


def get_tiles_for_polygon(polygon: Polygon, base_url: str) -> Set[Tuple[str, str, str, str]]:
    """
    Get all TIF tiles that intersect with the given polygon.
    
    Args:
        polygon: Shapely polygon in EPSG:3059 coordinates
        base_url: Base URL for downloading files
    
    Returns:
        Set of tuples (directory, filename_base, tif_url, tfw_url)
    """
    tiles = set()
    
    # Get bounding box (minx=min_easting, miny=min_northing, etc.)
    min_easting, min_northing, max_easting, max_northing = polygon.bounds
    
    # Round to nearest 2.5km grid
    min_tile_easting = int(min_easting / 2500) * 2500
    min_tile_northing = int(min_northing / 2500) * 2500
    max_tile_easting = int(max_easting / 2500) * 2500 + 2500
    max_tile_northing = int(max_northing / 2500) * 2500 + 2500
    
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
                center_easting = easting + 1250
                center_northing = northing + 1250
                
                directory, filename_base = calculate_tif_filename(center_easting, center_northing)
                
                # Remove trailing slash from base_url if present
                base_url_clean = base_url.rstrip('/')
                
                tif_url = f"{base_url_clean}/{directory}/{filename_base}.tif"
                tfw_url = f"{base_url_clean}/{directory}/{filename_base}.tfw"
                
                tiles.add((directory, filename_base, tif_url, tfw_url))
            
            easting += 2500
        northing += 2500
    
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
        description='Download georeferenced TIF images and world files covering a polygon area in EPSG:3059'
    )
    parser.add_argument(
        'base_url',
        type=str,
        help='Base URL for downloading TIF files'
    )
    parser.add_argument(
        'polygon',
        type=str,
        help='Polygon in WKT format, e.g., "POLYGON((x1 y1, x2 y2, ...))"'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='./tif_files',
        help='Output directory for downloaded files (default: ./tif_files)'
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
    tiles = get_tiles_for_polygon(polygon, args.base_url)
    
    if not tiles:
        print("No tiles found for the given polygon")
        return
    
    print(f"Found {len(tiles)} tiles covering the polygon")
    print()
    
    if args.list_only:
        print("URLs:")
        for directory, filename_base, tif_url, tfw_url in sorted(tiles):
            print(f"{tif_url}")
            print(f"{tfw_url}")
    else:
        # Download files
        output_dir = Path(args.output_dir)
        downloaded = 0
        skipped = 0
        failed = 0
        
        tiles_list = sorted(tiles)
        
        for i, (directory, filename_base, tif_url, tfw_url) in enumerate(tiles_list, 1):
            print(f"\n[{i}/{len(tiles_list)}] {filename_base}")
            
            # Download TIF file
            tif_path = output_dir / f"{filename_base}.tif"
            tif_result = download_file(tif_url, tif_path, curl_path=args.curl_path)
            
            # Download TFW file
            tfw_path = output_dir / f"{filename_base}.tfw"
            tfw_result = download_file(tfw_url, tfw_path, curl_path=args.curl_path)
            
            # Count as success if at least one file was downloaded
            if tif_result or tfw_result:
                downloaded += 1
            elif tif_path.exists() and tfw_path.exists():
                skipped += 1
            else:
                failed += 1
        
        print()
        print(f"Summary:")
        print(f"  Downloaded: {downloaded} tiles")
        print(f"  Skipped (already exist): {skipped} tiles")
        print(f"  Failed: {failed} tiles")


if __name__ == '__main__':
    main()
