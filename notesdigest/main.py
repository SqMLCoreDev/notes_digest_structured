#!/usr/bin/env python3
"""
Main Application Entry Point
Orchestrates applications and provides unified access point with concurrent processing support
"""

import sys
import argparse
import asyncio
from typing import List

def main():
    """
    Main application orchestrator
    Routes to different applications based on arguments or configuration
    """
    parser = argparse.ArgumentParser(description='Medical Notes Processing Suite - Concurrent Processing')
    parser.add_argument('--app', choices=['medical_notes'], 
                       default='medical_notes', help='Application to run')
    parser.add_argument('--note-id', type=str, help='Single note ID to process')
    parser.add_argument('--note-ids', type=str, nargs='+', help='Multiple note IDs to process concurrently')
    parser.add_argument('--action', choices=['process', 'status', 'health'], 
                       default='process', help='Action to perform')
    parser.add_argument('--concurrent', action='store_true', 
                       help='Enable concurrent processing (default for multiple note IDs)')
    
    args = parser.parse_args()
    
    try:
        if args.app == 'medical_notes':
            return run_medical_notes_app(args)
        else:
            print(f"Unknown application: {args.app}")
            return 1
            
    except Exception as e:
        print(f"Error running application: {str(e)}")
        return 1

def run_medical_notes_app(args) -> int:
    """
    Run the medical notes processing application with concurrent processing support
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        if args.action == 'process':
            # Determine which note IDs to process
            note_ids = []
            if args.note_ids:
                note_ids = args.note_ids
            elif args.note_id:
                note_ids = [args.note_id]
            else:
                print("Error: Either --note-id or --note-ids is required for processing")
                return 1
            
            # Process notes
            if len(note_ids) == 1 and not args.concurrent:
                # Single note processing (legacy mode)
                return process_single_note_legacy(note_ids[0])
            else:
                # Concurrent processing (default for multiple notes)
                return process_multiple_notes_concurrent(note_ids)
                
        elif args.action == 'health':
            print("Medical Notes App: Healthy (Concurrent Processing Enabled)")
            return 0
            
        elif args.action == 'status':
            return show_system_status()
            
    except ImportError as e:
        print(f"Error importing medical notes modules: {str(e)}")
        return 1
    except Exception as e:
        print(f"Error in medical notes app: {str(e)}")
        return 1

def process_single_note_legacy(note_id: str) -> int:
    """
    Process a single note using the legacy synchronous method.
    
    Args:
        note_id: Note ID to process
        
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    from medical_notes.service.medical_notes_processor import process_single_note
    
    print(f"Processing medical note: {note_id} (legacy mode)")
    result = process_single_note(note_id)
    
    if result.get('success'):
        print(f"✓ Successfully processed note {note_id}")
        return 0
    else:
        print(f"✗ Failed to process note {note_id}: {result.get('message', 'Unknown error')}")
        return 1

def process_multiple_notes_concurrent(note_ids: List[str]) -> int:
    """
    Process multiple notes using concurrent processing.
    
    Args:
        note_ids: List of note IDs to process
        
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    from medical_notes.service.concurrent_job_manager import get_job_manager
    import time
    
    print(f"🚀 Processing {len(note_ids)} medical notes concurrently...")
    
    job_manager = get_job_manager()
    
    # Submit all jobs using the full processing pipeline
    job_ids = []
    for note_id in note_ids:
        try:
            # Import the concurrent wrapper function
            from medical_notes.service.app import concurrent_process_note_wrapper
            
            job_id = job_manager.submit_job(
                note_id=note_id,
                process_function=concurrent_process_note_wrapper
            )
            job_ids.append(job_id)
            print(f"📝 Submitted job {job_id} for note {note_id}")
        except Exception as e:
            print(f"❌ Failed to submit job for note {note_id}: {str(e)}")
            return 1
    
    # Wait for all jobs to complete
    print(f"⏳ Waiting for {len(job_ids)} jobs to complete...")
    
    completed_count = 0
    failed_count = 0
    completed_jobs = set()
    failed_jobs = set()
    
    while len(completed_jobs) + len(failed_jobs) < len(job_ids):
        time.sleep(2)  # Check every 2 seconds
        
        for job_id in job_ids:
            if job_id in completed_jobs or job_id in failed_jobs:
                continue  # Already processed
                
            job_info = job_manager.get_job_status(job_id)
            if job_info:
                if job_info.status.value == 'completed':
                    completed_jobs.add(job_id)
                    completed_count += 1
                    print(f"✅ Job {job_id} completed successfully")
                elif job_info.status.value == 'failed':
                    failed_jobs.add(job_id)
                    failed_count += 1
                    print(f"❌ Job {job_id} failed: {job_info.error}")
    
    # Report final results
    print(f"\n📊 Processing Summary:")
    print(f"   Total notes: {len(note_ids)}")
    print(f"   Successful: {completed_count}")
    print(f"   Failed: {failed_count}")
    
    if failed_count == 0:
        print(f"🎉 All notes processed successfully!")
        return 0
    else:
        print(f"⚠️ {failed_count} notes failed to process")
        return 1

def show_system_status() -> int:
    """
    Show system status including concurrent processing statistics.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        from medical_notes.service.concurrent_job_manager import get_job_manager
        from medical_notes.service.rate_limiter import get_bedrock_rate_limiter
        from medical_notes.config.config import MAX_CONCURRENT_NOTES, MAX_QUEUE_SIZE
        
        job_manager = get_job_manager()
        rate_limiter = get_bedrock_rate_limiter()
        
        job_stats = job_manager.get_stats()
        rate_stats = rate_limiter.get_stats()
        
        print("📊 Medical Notes Processing System Status")
        print("=" * 50)
        print(f"Processing Mode: Concurrent")
        print(f"Max Workers: {MAX_CONCURRENT_NOTES}")
        print(f"Max Queue Size: {MAX_QUEUE_SIZE}")
        print()
        
        print("Job Statistics:")
        print(f"  Active Jobs: {job_stats['current_active']}")
        print(f"  Queued Jobs: {job_stats['current_queued']}")
        print(f"  Total Submitted: {job_stats['total_submitted']}")
        print(f"  Total Completed: {job_stats['total_completed']}")
        print(f"  Total Failed: {job_stats['total_failed']}")
        print()
        
        print("Rate Limiting:")
        print(f"  Total Requests: {rate_stats['total_requests']}")
        print(f"  Rate Limited: {rate_stats['rate_limited_count']}")
        print(f"  Available Tokens: {rate_stats['current_available_tokens']:.1f}")
        print(f"  Configured RPS: {rate_stats['configured_rps']}")
        
        return 0
        
    except Exception as e:
        print(f"Error getting system status: {str(e)}")
        return 1

def run_web_server():
    """
    Run the web server (FastAPI/Flask) if needed
    This can be called separately or integrated here
    """
    try:
        from medical_notes.service.app import app
        import uvicorn
        
        print("Starting concurrent medical notes web server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
    except ImportError as e:
        print(f"Error importing web server modules: {str(e)}")
        return 1
    except Exception as e:
        print(f"Error starting web server: {str(e)}")
        return 1

if __name__ == "__main__":
    # Check if we should run the web server instead
    if len(sys.argv) > 1 and sys.argv[1] == 'server':
        run_web_server()
    else:
        exit_code = main()
        sys.exit(exit_code)