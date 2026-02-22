"""Prophet-based cost forecasting service."""

from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pandas as pd
from prophet import Prophet
from google.cloud import bigquery

from xpol.types import ForecastData, ForecastPoint
from xpol.utils.helpers import get_date_range
from xpol.services.billing.base import BaseBillingService


class ForecastService(BaseBillingService):
    """Cost forecasting using Facebook Prophet."""
    
    def get_historical_daily_costs(
        self,
        days_back: int = 180,
        project_id: Optional[str] = None
    ) -> pd.DataFrame:
        """Get historical daily cost data for forecasting.
        
        Args:
            days_back: Number of days of historical data to fetch
            project_id: Filter by project ID (optional)
        
        Returns:
            DataFrame with columns: ds (date), y (cost)
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                DATE(usage_start_time) as date,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            {project_filter}
            GROUP BY date
            ORDER BY date
        """
        
        job_config = self._build_query_job_config(start_date_str, end_date_str, project_id=project_id)
        
        # Debug logging
        # print(f"[FORECAST DEBUG] Executing query:")
        # print(f"[FORECAST DEBUG] Start date: {start_date_str}, End date: {end_date_str}")
        # print(f"[FORECAST DEBUG] Dataset: {self.billing_dataset}")
        # print(f"[FORECAST DEBUG] Query:\n{query}")
        
        results = self.client.query(query, job_config=job_config).result()
        
        # print(f"[FORECAST DEBUG] Query returned {results.total_rows} rows")
        
        # Convert to DataFrame in Prophet format
        data = []
        for row in results:
            data.append({
                'ds': row.date,  # Prophet requires 'ds' column for dates
                'y': float(row.total_cost)  # Prophet requires 'y' column for values
            })
        
        df = pd.DataFrame(data)
        
        # Fill missing dates with 0 cost
        if not df.empty:
            df['ds'] = pd.to_datetime(df['ds'])
            df = df.set_index('ds').asfreq('D', fill_value=0).reset_index()
        
        return df
    
    def forecast_costs(
        self,
        forecast_days: int = 90,
        historical_days: int = 180,
        project_id: Optional[str] = None
    ) -> ForecastData:
        """Generate cost forecast using Prophet.
        
        Args:
            forecast_days: Number of days to forecast into the future
            historical_days: Number of days of historical data to use
            project_id: Filter by project ID (optional)
        
        Returns:
            ForecastData object with predictions
        """
        # Get historical data
        df = self.get_historical_daily_costs(historical_days, project_id)
        
        if df.empty or len(df) < 14:  # Need at least 2 weeks of data
            # Return empty forecast if insufficient data
            return ForecastData(
                forecast_points=[],
                total_predicted_cost=0.0,
                forecast_days=forecast_days,
                model_confidence=0.0,
                trend="unknown",
                generated_at=datetime.now().isoformat()
            )
        
        # Initialize and train Prophet model
        model = Prophet(
            changepoint_prior_scale=0.05,  # More conservative for billing data
            seasonality_mode='multiplicative',  # Costs often scale multiplicatively
            daily_seasonality=False,  # Daily costs usually don't have daily patterns
            weekly_seasonality=True,  # But might have weekly patterns
            yearly_seasonality=True if historical_days >= 365 else False
        )
        
        # Fit model
        model.fit(df)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=forecast_days)
        
        # Generate predictions
        forecast = model.predict(future)
        
        # Extract only future predictions (not historical)
        future_forecast = forecast[forecast['ds'] > df['ds'].max()].copy()
        
        # Create forecast points
        forecast_points = []
        for _, row in future_forecast.iterrows():
            forecast_points.append(ForecastPoint(
                date=row['ds'].strftime('%Y-%m-%d'),
                predicted_cost=max(0, float(row['yhat'])),  # Ensure non-negative
                lower_bound=max(0, float(row['yhat_lower'])),
                upper_bound=max(0, float(row['yhat_upper']))
            ))
        
        # Calculate total predicted cost
        total_predicted = sum(point.predicted_cost for point in forecast_points)
        
        # Calculate model confidence (based on uncertainty range)
        avg_uncertainty = future_forecast['yhat_upper'] - future_forecast['yhat_lower']
        avg_prediction = future_forecast['yhat']
        # Confidence: 1 - (relative uncertainty)
        confidence = max(0, 1 - (avg_uncertainty.mean() / max(avg_prediction.mean(), 1)))
        
        # Determine trend
        trend = self._determine_trend(df, future_forecast)
        
        return ForecastData(
            forecast_points=forecast_points,
            total_predicted_cost=total_predicted,
            forecast_days=forecast_days,
            model_confidence=float(confidence),
            trend=trend,
            generated_at=datetime.now().isoformat()
        )
    
    def forecast_service_cost(
        self,
        service_name: str,
        forecast_days: int = 90,
        historical_days: int = 180,
        project_id: Optional[str] = None
    ) -> ForecastData:
        """Generate cost forecast for a specific service.
        
        Args:
            service_name: GCP service name (e.g., 'Cloud Run')
            forecast_days: Number of days to forecast
            historical_days: Number of days of historical data
            project_id: Filter by project ID (optional)
        
        Returns:
            ForecastData object with predictions
        """
        # Get historical data for specific service
        df = self._get_service_historical_costs(service_name, historical_days, project_id)
        
        if df.empty or len(df) < 14:
            return ForecastData(
                forecast_points=[],
                total_predicted_cost=0.0,
                forecast_days=forecast_days,
                model_confidence=0.0,
                trend="unknown",
                generated_at=datetime.now().isoformat()
            )
        
        # Use same forecasting logic as general forecast
        model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_mode='multiplicative',
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True if historical_days >= 365 else False
        )
        
        model.fit(df)
        future = model.make_future_dataframe(periods=forecast_days)
        forecast = model.predict(future)
        
        future_forecast = forecast[forecast['ds'] > df['ds'].max()].copy()
        
        forecast_points = []
        for _, row in future_forecast.iterrows():
            forecast_points.append(ForecastPoint(
                date=row['ds'].strftime('%Y-%m-%d'),
                predicted_cost=max(0, float(row['yhat'])),
                lower_bound=max(0, float(row['yhat_lower'])),
                upper_bound=max(0, float(row['yhat_upper']))
            ))
        
        total_predicted = sum(point.predicted_cost for point in forecast_points)
        
        avg_uncertainty = future_forecast['yhat_upper'] - future_forecast['yhat_lower']
        avg_prediction = future_forecast['yhat']
        confidence = max(0, 1 - (avg_uncertainty.mean() / max(avg_prediction.mean(), 1)))
        
        trend = self._determine_trend(df, future_forecast)
        
        return ForecastData(
            forecast_points=forecast_points,
            total_predicted_cost=total_predicted,
            forecast_days=forecast_days,
            model_confidence=float(confidence),
            trend=trend,
            generated_at=datetime.now().isoformat()
        )
    
    def _get_service_historical_costs(
        self,
        service_name: str,
        days_back: int,
        project_id: Optional[str] = None
    ) -> pd.DataFrame:
        """Get historical daily costs for a specific service."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        
        # Build project filter
        project_filter, _ = self._build_project_filter(project_id=project_id)
        
        query = f"""
            SELECT 
                DATE(usage_start_time) as date,
                SUM(cost) as total_cost
            FROM {self._get_table_reference()}
            WHERE {self._get_date_filter_sql()}
            AND service.description = @service_name
            {project_filter}
            GROUP BY date
            ORDER BY date
        """
        
        job_config = self._build_query_job_config(
            start_date_str,
            end_date_str,
            project_id=project_id,
            additional_parameters=[
                bigquery.ScalarQueryParameter("service_name", "STRING", service_name)
            ]
        )
        
        results = self.client.query(query, job_config=job_config).result()
        
        data = []
        for row in results:
            data.append({
                'ds': row.date,
                'y': float(row.total_cost)
            })
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            df['ds'] = pd.to_datetime(df['ds'])
            df = df.set_index('ds').asfreq('D', fill_value=0).reset_index()
        
        return df
    
    def _determine_trend(self, historical: pd.DataFrame, forecast: pd.DataFrame) -> str:
        """Determine if costs are increasing, decreasing, or stable."""
        if historical.empty or forecast.empty:
            return "unknown"
        
        # Compare recent historical average with forecast average
        recent_avg = historical.tail(30)['y'].mean()
        forecast_avg = forecast['yhat'].mean()
        
        if recent_avg == 0:
            return "increasing" if forecast_avg > 0 else "stable"
        
        change_pct = ((forecast_avg - recent_avg) / recent_avg) * 100
        
        if change_pct > 5:
            return "increasing"
        elif change_pct < -5:
            return "decreasing"
        else:
            return "stable"
