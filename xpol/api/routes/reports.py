"""Reports API routes."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from datetime import datetime

from xpol.api.config import get_cached_dashboard_data, REPORTS_DIR
from xpol.utils.reports import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate")
async def generate_report(
    format: str = Query("pdf", description="Report format (currently only 'pdf' supported)")
):
    """
    Generate a new PDF report and save it to the reports directory.
    
    Returns metadata about the generated report including download URL.
    """
    try:
        # Get dashboard data
        data = get_cached_dashboard_data()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"xpol-report-{timestamp}.pdf"
        output_path = REPORTS_DIR / filename
        
        # Generate the report - pass REPORTS_DIR so temp files are created there
        report_gen = ReportGenerator(output_dir=str(REPORTS_DIR))
        report_gen.generate_report(data, str(output_path))
        
        # Get file size
        file_size = output_path.stat().st_size
        
        return {
            "success": True,
            "filename": filename,
            "size": f"{file_size / 1024:.1f} KB",
            "size_bytes": file_size,
            "created_at": datetime.now().isoformat(),
            "download_url": f"/api/reports/{filename}/download",
            "project_id": data.project_id,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("")
async def list_reports():
    """
    List all generated reports from the reports directory.
    
    Returns list of reports with metadata sorted by creation date (newest first).
    """
    try:
        reports = []
        
        # Scan reports directory for PDF files
        for file_path in REPORTS_DIR.glob("*.pdf"):
            stat = file_path.stat()
            
            # Extract project ID from filename if possible
            # Format: xpol-report-{timestamp}.pdf
            project_id = None
            if file_path.stem.startswith("xpol-report-"):
                parts = file_path.stem.split("-")
                if len(parts) >= 5:
                    project_id = "-".join(parts[3:-2])  # Everything between "report" and timestamp
            
            reports.append({
                "filename": file_path.name,
                "size": f"{stat.st_size / 1024:.1f} KB",
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "download_url": f"/api/reports/{file_path.name}/download",
                "project_id": project_id,
            })
        
        # Sort by creation time (newest first)
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "reports": reports,
            "total": len(reports),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@router.get("/{filename}/download")
async def download_report(filename: str):
    """
    Download a specific report by filename.
    
    Returns the PDF file for download.
    """
    try:
        file_path = REPORTS_DIR / filename
        
        # Security check: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=filename,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")


@router.delete("/{filename}")
async def delete_report(filename: str):
    """
    Delete a specific report by filename.
    
    Returns success message.
    """
    try:
        file_path = REPORTS_DIR / filename
        
        # Security check: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Delete the file
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"Report '{filename}' deleted successfully",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")

