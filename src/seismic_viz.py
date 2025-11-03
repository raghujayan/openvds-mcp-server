"""
Seismic Visualization Module

Generates seismic images with proper colormaps and annotations
for display in Claude via MCP ImageContent
"""

import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import logging
from typing import Optional, Tuple, Dict, Any
from PIL import Image

logger = logging.getLogger("seismic-viz")


class SeismicColorMaps:
    """Standard seismic colormaps"""

    @staticmethod
    def seismic():
        """Red-White-Blue seismic colormap (classic)"""
        colors = ['#0000FF', '#FFFFFF', '#FF0000']  # Blue-White-Red
        return LinearSegmentedColormap.from_list('seismic', colors)

    @staticmethod
    def seismic_gray():
        """Grayscale for amplitude display"""
        return 'gray'

    @staticmethod
    def seismic_petrel():
        """Petrel-style colormap"""
        colors = [
            '#000080',  # Dark blue
            '#0000FF',  # Blue
            '#00FFFF',  # Cyan
            '#FFFFFF',  # White
            '#FFFF00',  # Yellow
            '#FF0000',  # Red
            '#800000'   # Dark red
        ]
        return LinearSegmentedColormap.from_list('petrel', colors)


class SeismicVisualizer:
    """Generate seismic images for MCP display"""

    def __init__(self, dpi: int = 100, figsize: Tuple[int, int] = (10, 8)):
        self.dpi = dpi
        self.figsize = figsize
        self.colormaps = SeismicColorMaps()

    def create_inline_image(
        self,
        data: np.ndarray,
        inline_number: int,
        crossline_range: Tuple[int, int],
        sample_range: Tuple[int, int],
        colormap: str = 'seismic',
        title: Optional[str] = None,
        clip_percentile: float = 99.0
    ) -> bytes:
        """
        Create inline seismic image

        Args:
            data: 2D array [crosslines, samples]
            inline_number: Inline number for title
            crossline_range: (min, max) crossline numbers
            sample_range: (min, max) sample values (time/depth)
            colormap: 'seismic', 'gray', or 'petrel'
            title: Optional custom title
            clip_percentile: Percentile for amplitude clipping

        Returns:
            PNG image as bytes
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        # Get colormap
        cmap = self._get_colormap(colormap)

        # Calculate amplitude clipping
        vmin, vmax = self._calculate_clip_range(data, clip_percentile)

        # Display image
        extent = [
            crossline_range[0], crossline_range[1],  # X-axis
            sample_range[1], sample_range[0]  # Y-axis (reversed for depth/time)
        ]

        im = ax.imshow(
            data.T,  # Transpose for proper orientation
            aspect='auto',
            cmap=cmap,
            extent=extent,
            vmin=vmin,
            vmax=vmax,
            interpolation='bilinear'
        )

        # Labels and title
        ax.set_xlabel('Crossline', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time/Depth (samples)', fontsize=12, fontweight='bold')

        if title:
            ax.set_title(title, fontsize=14, fontweight='bold')
        else:
            ax.set_title(f'Inline {inline_number}', fontsize=14, fontweight='bold')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label='Amplitude')
        cbar.ax.tick_params(labelsize=10)

        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Add statistics text
        stats_text = f'Min: {data.min():.2f}\nMax: {data.max():.2f}\nMean: {data.mean():.2f}'
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )

        plt.tight_layout()

        # Convert to PNG bytes
        img_bytes = self._fig_to_bytes(fig)
        plt.close(fig)

        return img_bytes

    def create_crossline_image(
        self,
        data: np.ndarray,
        crossline_number: int,
        inline_range: Tuple[int, int],
        sample_range: Tuple[int, int],
        colormap: str = 'seismic',
        title: Optional[str] = None,
        clip_percentile: float = 99.0
    ) -> bytes:
        """
        Create crossline seismic image

        Args:
            data: 2D array [inlines, samples]
            crossline_number: Crossline number for title
            inline_range: (min, max) inline numbers
            sample_range: (min, max) sample values
            colormap: 'seismic', 'gray', or 'petrel'
            title: Optional custom title
            clip_percentile: Percentile for amplitude clipping

        Returns:
            PNG image as bytes
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        # Get colormap
        cmap = self._get_colormap(colormap)

        # Calculate amplitude clipping
        vmin, vmax = self._calculate_clip_range(data, clip_percentile)

        # Display image
        extent = [
            inline_range[0], inline_range[1],
            sample_range[1], sample_range[0]
        ]

        im = ax.imshow(
            data.T,
            aspect='auto',
            cmap=cmap,
            extent=extent,
            vmin=vmin,
            vmax=vmax,
            interpolation='bilinear'
        )

        # Labels and title
        ax.set_xlabel('Inline', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time/Depth (samples)', fontsize=12, fontweight='bold')

        if title:
            ax.set_title(title, fontsize=14, fontweight='bold')
        else:
            ax.set_title(f'Crossline {crossline_number}', fontsize=14, fontweight='bold')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label='Amplitude')
        cbar.ax.tick_params(labelsize=10)

        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Add statistics
        stats_text = f'Min: {data.min():.2f}\nMax: {data.max():.2f}\nMean: {data.mean():.2f}'
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )

        plt.tight_layout()

        # Convert to PNG bytes
        img_bytes = self._fig_to_bytes(fig)
        plt.close(fig)

        return img_bytes

    def create_timeslice_image(
        self,
        data: np.ndarray,
        time_value: int,
        inline_range: Tuple[int, int],
        crossline_range: Tuple[int, int],
        colormap: str = 'seismic',
        title: Optional[str] = None,
        clip_percentile: float = 99.0
    ) -> bytes:
        """
        Create time/depth slice (map view) image

        Args:
            data: 2D array [inlines, crosslines]
            time_value: Time/depth value for title
            inline_range: (min, max) inline numbers
            crossline_range: (min, max) crossline numbers
            colormap: 'seismic', 'gray', or 'petrel'
            title: Optional custom title
            clip_percentile: Percentile for amplitude clipping

        Returns:
            PNG image as bytes
        """
        # Adaptive downsampling for large images
        max_pixels = 800 * 600  # Max ~480k pixels
        current_pixels = data.shape[0] * data.shape[1]

        if current_pixels > max_pixels:
            # Downsample to reduce size
            downsample_factor = int(np.sqrt(current_pixels / max_pixels)) + 1
            logger.info(f"Downsampling timeslice by factor {downsample_factor} ({current_pixels} -> ~{current_pixels//downsample_factor**2} pixels)")
            data = data[::downsample_factor, ::downsample_factor]

        # Use lower DPI for timeslices
        dpi = 72  # Reduce from 100 to 72 for timeslices

        fig, ax = plt.subplots(figsize=self.figsize, dpi=dpi)

        # Get colormap
        cmap = self._get_colormap(colormap)

        # Calculate amplitude clipping
        vmin, vmax = self._calculate_clip_range(data, clip_percentile)

        # Display image
        extent = [
            crossline_range[0], crossline_range[1],
            inline_range[0], inline_range[1]
        ]

        im = ax.imshow(
            data,
            aspect='auto',
            cmap=cmap,
            extent=extent,
            origin='lower',
            vmin=vmin,
            vmax=vmax,
            interpolation='bilinear'
        )

        # Labels and title
        ax.set_xlabel('Crossline', fontsize=12, fontweight='bold')
        ax.set_ylabel('Inline', fontsize=12, fontweight='bold')

        if title:
            ax.set_title(title, fontsize=14, fontweight='bold')
        else:
            ax.set_title(f'Time/Depth Slice @ {time_value}', fontsize=14, fontweight='bold')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label='Amplitude')
        cbar.ax.tick_params(labelsize=10)

        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Add statistics
        stats_text = f'Min: {data.min():.2f}\nMax: {data.max():.2f}\nMean: {data.mean():.2f}'
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )

        plt.tight_layout()

        # Convert to PNG bytes with custom DPI
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=dpi)
        buf.seek(0)
        img_bytes = buf.read()
        buf.close()
        plt.close(fig)

        return img_bytes

    def _get_colormap(self, colormap: str):
        """Get colormap object"""
        if colormap == 'seismic':
            return self.colormaps.seismic()
        elif colormap == 'gray':
            return self.colormaps.seismic_gray()
        elif colormap == 'petrel':
            return self.colormaps.seismic_petrel()
        else:
            logger.warning(f"Unknown colormap '{colormap}', using 'seismic'")
            return self.colormaps.seismic()

    def _calculate_clip_range(
        self,
        data: np.ndarray,
        percentile: float
    ) -> Tuple[float, float]:
        """Calculate amplitude clipping range based on percentile"""
        # Remove NaN values for percentile calculation
        valid_data = data[~np.isnan(data)]

        if len(valid_data) == 0:
            return 0.0, 1.0

        # Symmetric clipping around zero
        abs_max = np.percentile(np.abs(valid_data), percentile)
        return -abs_max, abs_max

    def _fig_to_bytes(self, fig) -> bytes:
        """Convert matplotlib figure to PNG bytes"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=self.dpi)
        buf.seek(0)
        img_bytes = buf.read()
        buf.close()
        return img_bytes

    def compress_image(
        self,
        img_bytes: bytes,
        max_size_kb: int = 800
    ) -> bytes:
        """
        Compress image if larger than max_size_kb

        Keeps image under MCP 1MB limit while maintaining quality.
        Uses JPEG for better compression if PNG optimization isn't enough.
        """
        size_kb = len(img_bytes) / 1024

        if size_kb <= max_size_kb:
            return img_bytes

        logger.info(f"Compressing image from {size_kb:.1f} KB to ~{max_size_kb} KB")

        # Open image
        img = Image.open(io.BytesIO(img_bytes))

        # Try PNG optimization first
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True, compress_level=9)
        buf.seek(0)
        compressed_bytes = buf.read()
        buf.close()

        new_size_kb = len(compressed_bytes) / 1024

        # If still too large, convert to JPEG
        if new_size_kb > max_size_kb:
            logger.info(f"PNG optimization insufficient ({new_size_kb:.1f} KB), converting to JPEG")

            # Convert to RGB (JPEG doesn't support RGBA)
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])  # Use alpha as mask
                img = rgb_img

            # Calculate JPEG quality
            quality = int(85 * (max_size_kb / new_size_kb))
            quality = max(60, min(95, quality))

            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            buf.seek(0)
            compressed_bytes = buf.read()
            buf.close()

            new_size_kb = len(compressed_bytes) / 1024
            logger.info(f"JPEG compressed to {new_size_kb:.1f} KB (quality={quality})")

        else:
            logger.info(f"PNG optimized to {new_size_kb:.1f} KB")

        return compressed_bytes


# Global visualizer instance
_visualizer: Optional[SeismicVisualizer] = None


def get_visualizer() -> SeismicVisualizer:
    """Get global visualizer instance"""
    global _visualizer
    if _visualizer is None:
        _visualizer = SeismicVisualizer()
    return _visualizer
