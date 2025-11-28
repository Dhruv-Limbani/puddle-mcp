from puddle_server.mcp import mcp
from puddle_server.utils import run_pg_sql, get_embedding
from typing import Optional, List

# ==========================================
# HELPER FORMATTERS
# ==========================================

def format_vendor_str(v: dict) -> str:
    """Helper to format a single vendor record."""
    loc = [v.get('city'), v.get('region'), v.get('country')]
    location_str = ", ".join(filter(None, loc))
    
    return (
        f"VENDOR: {v['name']}\n"
        f" - Type: {v.get('organization_type', 'N/A')} (Founded: {v.get('founded_year', 'N/A')})\n"
        f" - Industry: {v.get('industry_focus', 'N/A')}\n"
        f" - Location: {location_str}\n"
        f" - Description: {v.get('description', 'No description available.')}"
    )

def format_dataset_str(d: dict, score: float = None) -> str:
    """Helper to format a single dataset record."""
    score_str = f" (Match Score: {score:.2f})" if score else ""
    
    return (
        f"DATASET: {d['title']}{score_str}\n"
        f" - ID: {d['id']}\n"
        f" - Vendor: {d.get('vendor_name', 'Unknown')}\n"
        f" - Domain: {d.get('domain', 'N/A')} | Pricing: {d.get('pricing_model', 'N/A')}\n"
        f" - Description: {d.get('description', 'No description.')}"
    )

# ==========================================
# VENDOR TOOLS
# ==========================================

@mcp.tool()
def search_vendors(query: str, limit: int = 5) -> str:
    """
    Search for vendors by name or industry focus. 
    Returns a summarized list of vendors found.
    """
    sql = """
        SELECT 
            id, name, industry_focus, description, 
            country, region, city, organization_type, founded_year
        FROM vendors
        WHERE 
            name ILIKE %s OR 
            industry_focus ILIKE %s
        LIMIT %s;
    """
    search_term = f"%{query}%"
    results = run_pg_sql(sql, (search_term, search_term, limit))
    
    if not results:
        return "No vendors found matching your criteria."
        
    # Stitch results into a readable list
    output = [f"Found {len(results)} vendors matching '{query}':\n"]
    for v in results:
        output.append(format_vendor_str(v))
        output.append("---")
        
    return "\n".join(output)

@mcp.tool()
def get_vendor_details(vendor_id: str) -> str:
    """
    Retrieve public detailed information about a specific vendor.
    """
    sql = """
        SELECT 
            name, industry_focus, description, 
            website_url, country, region, city, 
            organization_type, founded_year
        FROM vendors
        WHERE id = %s;
    """
    v = run_pg_sql(sql, (vendor_id,), fetch_one=True)
    
    if not v:
        return "Vendor not found."
    
    loc = [v.get('city'), v.get('region'), v.get('country')]
    location_str = ", ".join(filter(None, loc))

    return (
        f"=== VENDOR PROFILE ===\n"
        f"Name: {v['name']}\n"
        f"Website: {v.get('website_url', 'N/A')}\n"
        f"Location: {location_str}\n"
        f"Industry: {v.get('industry_focus')}\n"
        f"Org Type: {v.get('organization_type')} (Est. {v.get('founded_year')})\n\n"
        f"ABOUT:\n{v.get('description')}"
    )

# ==========================================
# DATASET TOOLS
# ==========================================

@mcp.tool()
def search_datasets_semantic(query: str, limit: int = 5) -> str:
    """
    Performs a semantic search to find relevant datasets.
    Returns a ranked list of datasets with relevance scores.
    """
    query_embedding = get_embedding(query)
    
    sql = """
        SELECT 
            d.id, d.title, d.description,
            v.name as vendor_name,
            d.domain, d.pricing_model,
            1 - (d.embedding <=> %s::vector) as similarity_score
        FROM datasets d
        JOIN vendors v ON d.vendor_id = v.id
        WHERE d.visibility = 'public' 
          AND d.status = 'active'
        ORDER BY d.embedding <=> %s::vector
        LIMIT %s;
    """
    
    results = run_pg_sql(sql, (str(query_embedding), str(query_embedding), limit))
    
    if not results:
        return "No relevant datasets found."
        
    output = [f"Found {len(results)} datasets relevant to: '{query}':\n"]
    
    for d in results:
        output.append(format_dataset_str(d, score=d['similarity_score']))
        output.append("---")
        
    return "\n".join(output)

@mcp.tool()
def filter_datasets(
    domain: Optional[str] = None, 
    price_model: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Filter datasets by structured attributes (Domain, Pricing).
    """
    sql = """
        SELECT d.id, d.title, d.domain, d.pricing_model, d.description, v.name as vendor_name
        FROM datasets d
        JOIN vendors v ON d.vendor_id = v.id
        WHERE d.visibility = 'public' AND d.status = 'active'
    """
    params = []
    
    if domain:
        sql += " AND d.domain ILIKE %s"
        params.append(f"%{domain}%")
    
    if price_model:
        sql += " AND d.pricing_model ILIKE %s"
        params.append(f"%{price_model}%")
        
    sql += " LIMIT %s"
    params.append(limit)
    
    results = run_pg_sql(sql, tuple(params))
    
    if not results:
        return "No datasets found matching the applied filters."

    output = [f"Filtered Search Results ({len(results)} found):\n"]
    for d in results:
        output.append(format_dataset_str(d))
        output.append("---")
        
    return "\n".join(output)

@mcp.tool()
def get_dataset_details_complete(dataset_id: str) -> str:
    """
    Retrieves COMPLETE details about a dataset, formatted as a report.
    Includes Metadata and Schema (Column definitions).
    """
    # 1. Get Metadata
    meta_sql = """
        SELECT 
            d.title, d.description, d.domain, d.granularity, 
            d.pricing_model, d.license, 
            d.temporal_coverage, d.geographic_coverage,
            v.name as vendor_name, v.contact_email as vendor_contact
        FROM datasets d
        JOIN vendors v ON d.vendor_id = v.id
        WHERE d.id = %s AND d.visibility = 'public';
    """
    meta = run_pg_sql(meta_sql, (dataset_id,), fetch_one=True)
    
    if not meta:
        return "Dataset not found or is private."

    # 2. Get Columns
    col_sql = """
        SELECT name, description, data_type, sample_values
        FROM dataset_columns
        WHERE dataset_id = %s;
    """
    columns = run_pg_sql(col_sql, (dataset_id,))
    
    # 3. Build the Report
    report = []
    
    # --- Header ---
    report.append(f"=== DATASET REPORT: {meta['title']} ===")
    report.append(f"Vendor: {meta['vendor_name']} (Contact: {meta['vendor_contact']})")
    report.append(f"Domain: {meta['domain']} | License: {meta.get('license', 'N/A')}")
    report.append(f"Pricing: {meta['pricing_model']} | Granularity: {meta.get('granularity', 'N/A')}")
    
    # --- Description ---
    report.append(f"\nDESCRIPTION:\n{meta['description']}")
    
    # --- Coverage ---
    geo = meta.get('geographic_coverage') or "Global"
    temp = meta.get('temporal_coverage') or "N/A"
    report.append(f"\nCOVERAGE:\n- Geography: {geo}\n- Time Range: {temp}")
    
    # --- Schema ---
    report.append(f"\n=== SCHEMA ({len(columns)} Columns) ===")
    if columns:
        for col in columns:
            # Handle sample values safely
            samples = col.get('sample_values')
            sample_str = f" (Samples: {samples})" if samples else ""
            
            report.append(
                f"- {col['name']} ({col['data_type']}): {col.get('description', 'No desc')} {sample_str}"
            )
    else:
        report.append("No column metadata available.")
        
    return "\n".join(report)