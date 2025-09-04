
import streamlit as st
import io
from PIL import Image
import os
from io import BytesIO

def get_streamlit_version():
    """Get Streamlit version to handle compatibility"""
    try:
        import streamlit as st
        version = st.__version__
        major, minor = map(int, version.split('.')[:2])
        return major, minor
    except:
        return 1, 0  # Default to old version if can't determine

def display_image(image, caption, **kwargs):
    """Display image with version compatibility"""
    try:
        major, minor = get_streamlit_version()
        # use_container_width was introduced in 1.14.0
        if major > 1 or (major == 1 and minor >= 14):
            st.image(image, caption=caption, use_container_width=True)
        else:
            # Use the old parameter name for older versions
            st.image(image, caption=caption, use_column_width=True)
    except:
        # Fallback to basic image display
        st.image(image, caption=caption)

def get_image_size(image_bytes):
    """Get the size of image in KB"""
    return len(image_bytes) / 1024

def prepare_image_for_webp(image, preserve_transparency=True):
    """
    Prepare image for WebP conversion while handling transparency properly

    Args:
        image: PIL Image object
        preserve_transparency: Whether to preserve transparency or use white background

    Returns:
        PIL Image object ready for WebP conversion
    """
    original_mode = image.mode

    if original_mode == "RGBA":
        if preserve_transparency:
            # Keep RGBA for transparent WebP
            return image
        else:
            # Composite onto white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
            return background

    elif original_mode == "P":
        # Handle palette images
        if 'transparency' in image.info:
            if preserve_transparency:
                # Convert to RGBA to preserve transparency
                image = image.convert('RGBA')
                return image
            else:
                # Convert to RGB with white background
                image = image.convert('RGBA')
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                return background
        else:
            # No transparency, convert to RGB
            return image.convert('RGB')

    elif original_mode in ("L", "LA"):
        # Grayscale images
        if original_mode == "LA" and preserve_transparency:
            # Convert to RGBA to preserve alpha
            return image.convert('RGBA')
        else:
            # Convert to RGB
            return image.convert('RGB')

    else:
        # RGB, CMYK, etc. - convert to RGB if needed
        if original_mode != "RGB":
            return image.convert('RGB')
        return image

def compress_image(image, target_size_kb=500, quality=85, max_width=1920, max_height=1080, preserve_transparency=True):
    """
    Compress image to target size and convert to WebP format

    Args:
        image: PIL Image object
        target_size_kb: Target file size in KB
        quality: Initial quality (0-100)
        max_width: Maximum width for desktop
        max_height: Maximum height for desktop
        preserve_transparency: Whether to preserve transparency

    Returns:
        tuple: (compressed_image_bytes, final_quality, final_dimensions, has_transparency)
    """

    # Check if original image has transparency
    has_transparency = image.mode in ("RGBA", "LA") or (image.mode == "P" and 'transparency' in image.info)

    # Prepare image for WebP conversion
    image = prepare_image_for_webp(image, preserve_transparency and has_transparency)

    # Calculate resize ratio to fit within max dimensions
    width, height = image.size
    resize_ratio = min(max_width / width, max_height / height, 1.0)

    if resize_ratio < 1.0:
        new_width = int(width * resize_ratio)
        new_height = int(height * resize_ratio)
        # Use LANCZOS for better quality with transparency
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Binary search for optimal quality
    low_quality = 1
    high_quality = quality
    best_quality = quality
    best_image_bytes = None

    while low_quality <= high_quality:
        current_quality = (low_quality + high_quality) // 2

        # Save image with current quality
        img_buffer = BytesIO()

        # Save with appropriate options for transparency
        save_options = {
            'format': 'WebP',
            'quality': current_quality,
            'optimize': True
        }

        # Add lossless option for very high quality with transparency
        if has_transparency and preserve_transparency and current_quality > 90:
            save_options['lossless'] = True
            save_options.pop('quality')  # lossless mode doesn't use quality

        image.save(img_buffer, **save_options)
        img_bytes = img_buffer.getvalue()
        img_size_kb = len(img_bytes) / 1024

        if img_size_kb <= target_size_kb:
            best_quality = current_quality
            best_image_bytes = img_bytes
            low_quality = current_quality + 1
        else:
            high_quality = current_quality - 1

    # If we couldn't achieve target size, try further resizing
    if best_image_bytes is None or get_image_size(best_image_bytes) > target_size_kb:
        # Reduce dimensions further
        current_width, current_height = image.size
        reduction_factor = 0.8

        while get_image_size(best_image_bytes or img_bytes) > target_size_kb and reduction_factor > 0.3:
            new_width = int(current_width * reduction_factor)
            new_height = int(current_height * reduction_factor)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            img_buffer = BytesIO()

            # Use the same save options as before
            save_options = {
                'format': 'WebP',
                'quality': best_quality,
                'optimize': True
            }

            resized_image.save(img_buffer, **save_options)
            img_bytes = img_buffer.getvalue()

            if len(img_bytes) / 1024 <= target_size_kb:
                best_image_bytes = img_bytes
                image = resized_image
                break

            reduction_factor -= 0.1

    final_dimensions = image.size
    return best_image_bytes or img_bytes, best_quality, final_dimensions, has_transparency

def create_mobile_version(image, max_width=768, preserve_transparency=True):
    """Create mobile-friendly version of image"""
    # Check if original image has transparency
    has_transparency = image.mode in ("RGBA", "LA") or (image.mode == "P" and 'transparency' in image.info)

    # Prepare image for WebP conversion
    image = prepare_image_for_webp(image, preserve_transparency and has_transparency)

    width, height = image.size
    if width > max_width:
        ratio = max_width / width
        new_height = int(height * ratio)
        image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

    img_buffer = BytesIO()

    # Save with appropriate options for transparency
    save_options = {
        'format': 'WebP',
        'quality': 80,
        'optimize': True
    }

    image.save(img_buffer, **save_options)
    return img_buffer.getvalue(), image.size, has_transparency

def display_footer():
    """Display footer with creator credit"""
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #fff; font-size: 14px; padding: 10px 0;'>
            Created by <strong><a href="https://pandyadhruv.com/" target="_blank">Dhruv Pandya</a></strong>
        </div>
        """, 
        unsafe_allow_html=True
    )

def main():
    st.set_page_config(
        page_title="Image Compressor & WebP Converter",
        page_icon="🖼️",
        layout="wide"
    )

    st.title("🖼️ Image Compressor & WebP Converter")
    st.write("Upload your image and compress it to WebP format with custom size limits!")
    
    # Sidebar for settings
    st.sidebar.header("⚙️ Compression Settings")
    target_size = st.sidebar.number_input(
        "Target file size (KB)", 
        min_value=10, 
        max_value=5000, 
        value=500, 
        step=10,
        help="Maximum file size for the compressed image"
    )

    initial_quality = st.sidebar.slider(
        "Initial Quality", 
        min_value=10, 
        max_value=100, 
        value=85,
        help="Starting quality for compression (will be optimized automatically)"
    )

    # Transparency handling option
    st.sidebar.subheader("🎭 Transparency Options")
    preserve_transparency = st.sidebar.checkbox(
        "Preserve Transparency", 
        value=True,
        help="Keep transparent areas transparent (recommended for PNG with transparency)"
    )

    if not preserve_transparency:
        background_color = st.sidebar.color_picker(
            "Background Color", 
            value="#FFFFFF",
            help="Color to use for transparent areas when transparency is not preserved"
        )

    st.sidebar.subheader("📱 Responsive Sizes")
    desktop_width = st.sidebar.number_input(
        "Desktop max width (px)", 
        min_value=800, 
        max_value=4000, 
        value=1920, 
        step=100
    )

    desktop_height = st.sidebar.number_input(
        "Desktop max height (px)", 
        min_value=600, 
        max_value=3000, 
        value=1080, 
        step=100
    )

    mobile_width = st.sidebar.number_input(
        "Mobile max width (px)", 
        min_value=320, 
        max_value=1024, 
        value=768, 
        step=50
    )

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'],
        help="Supported formats: PNG, JPG, JPEG, BMP, TIFF, WebP"
    )

    if uploaded_file is not None:
        try:
            # Display original image info
            original_bytes = uploaded_file.getvalue()
            original_size_kb = len(original_bytes) / 1024

            # Open image
            image = Image.open(uploaded_file)
            original_width, original_height = image.size

            # Check for transparency
            has_transparency = image.mode in ("RGBA", "LA") or (image.mode == "P" and 'transparency' in image.info)

            # Display original image details
            st.subheader("📊 Original Image Details")
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("File Size", f"{original_size_kb:.1f} KB")
            with col2:
                st.metric("Format", uploaded_file.type.split('/')[-1].upper())
            with col3:
                st.metric("Dimensions", f"{original_width} × {original_height}")
            with col4:
                st.metric("Mode", image.mode)
            with col5:
                transparency_status = "✅ Yes" if has_transparency else "❌ No"
                st.metric("Transparency", transparency_status)

            # Show transparency warning/info
            if has_transparency:
                if preserve_transparency:
                    st.success("🎭 Transparency detected and will be preserved in WebP output!")
                else:
                    st.warning("🎭 Transparency detected but will be replaced with background color.")

            # Show original image using compatibility function
            st.subheader("🖼️ Original Image")
            display_image(image, f"Original: {uploaded_file.name}")

            # Compress button
            if st.button("🚀 Compress Image", type="primary"):
                with st.spinner("Compressing image... This may take a moment."):
                    # Compress for desktop
                    desktop_compressed, desktop_quality, desktop_dims, desktop_has_transparency = compress_image(
                        image.copy(), target_size, initial_quality, desktop_width, desktop_height, preserve_transparency
                    )

                    # Create mobile version
                    mobile_compressed, mobile_dims, mobile_has_transparency = create_mobile_version(
                        image.copy(), mobile_width, preserve_transparency
                    )

                    # Calculate compression stats
                    desktop_size_kb = len(desktop_compressed) / 1024
                    mobile_size_kb = len(mobile_compressed) / 1024

                    desktop_reduction = ((original_size_kb - desktop_size_kb) / original_size_kb) * 100
                    mobile_reduction = ((original_size_kb - mobile_size_kb) / original_size_kb) * 100

                # Display results
                st.success("✅ Compression completed!")

                # Results comparison
                st.subheader("📈 Compression Results")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write("**Original**")
                    st.metric("Size", f"{original_size_kb:.1f} KB")
                    st.metric("Dimensions", f"{original_width} × {original_height}")
                    st.metric("Format", uploaded_file.type.split('/')[-1].upper())
                    transparency_text = "✅ Yes" if has_transparency else "❌ No"
                    st.metric("Transparency", transparency_text)

                with col2:
                    st.write("**Desktop (WebP)**")
                    st.metric("Size", f"{desktop_size_kb:.1f} KB", f"-{desktop_reduction:.1f}%")
                    st.metric("Dimensions", f"{desktop_dims[0]} × {desktop_dims[1]}")
                    st.metric("Quality", f"{desktop_quality}%")
                    desktop_transparency_text = "✅ Preserved" if (desktop_has_transparency and preserve_transparency) else "❌ Removed"
                    st.metric("Transparency", desktop_transparency_text)

                with col3:
                    st.write("**Mobile (WebP)**")
                    st.metric("Size", f"{mobile_size_kb:.1f} KB", f"-{mobile_reduction:.1f}%")
                    st.metric("Dimensions", f"{mobile_dims[0]} × {mobile_dims[1]}")
                    st.metric("Optimized for", "Mobile devices")
                    mobile_transparency_text = "✅ Preserved" if (mobile_has_transparency and preserve_transparency) else "❌ Removed"
                    st.metric("Transparency", mobile_transparency_text)

                # Display compressed images using compatibility function
                st.subheader("🖥️ Desktop Version")
                desktop_image = Image.open(BytesIO(desktop_compressed))
                display_image(desktop_image, f"Desktop WebP: {desktop_size_kb:.1f} KB")

                st.subheader("📱 Mobile Version")
                mobile_image = Image.open(BytesIO(mobile_compressed))
                display_image(mobile_image, f"Mobile WebP: {mobile_size_kb:.1f} KB")

                # Download buttons
                st.subheader("⬇️ Download Compressed Images")

                col1, col2 = st.columns(2)

                with col1:
                    desktop_filename = f"{os.path.splitext(uploaded_file.name)[0]}_desktop.webp"
                    st.download_button(
                        label="📥 Download Desktop Version",
                        data=desktop_compressed,
                        file_name=desktop_filename,
                        mime="image/webp"
                    )

                with col2:
                    mobile_filename = f"{os.path.splitext(uploaded_file.name)[0]}_mobile.webp"
                    st.download_button(
                        label="📥 Download Mobile Version",
                        data=mobile_compressed,
                        file_name=mobile_filename,
                        mime="image/webp"
                    )

                # Additional info
                st.subheader("ℹ️ Compression Info")
                transparency_info = ""
                if has_transparency:
                    if preserve_transparency:
                        transparency_info = """
                **Transparency Handling:**
                - Original transparency has been preserved in WebP format
                - WebP supports both lossy and lossless transparency
                - Transparent areas remain fully transparent
                """
                    else:
                        transparency_info = f"""
                **Transparency Handling:**
                - Original transparency has been replaced with solid background
                - Background color used: {background_color if not preserve_transparency else '#FFFFFF'}
                - File size may be smaller without transparency
                """

                st.info(f"""
                **Desktop Version:**
                - Optimized for screens up to {desktop_width}×{desktop_height}px
                - Quality automatically adjusted to {desktop_quality}% to meet size target
                - Size reduction: {desktop_reduction:.1f}%

                **Mobile Version:**
                - Optimized for mobile screens (max width: {mobile_width}px)
                - Fixed quality at 80% for good mobile performance
                - Size reduction: {mobile_reduction:.1f}%

                **WebP Benefits:**
                - Superior compression compared to JPEG/PNG
                - Supports transparency and animation
                - Widely supported by modern browsers
                - Up to 35% smaller than PNG with transparency
                {transparency_info}
                """)

        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            st.write("Please make sure you've uploaded a valid image file.")

            # Debug information
            with st.expander("🔧 Debug Information"):
                st.write(f"Streamlit version: {st.__version__}")
                st.write(f"Error details: {type(e).__name__}: {str(e)}")
                if 'image' in locals():
                    st.write(f"Image mode: {image.mode}")
                    st.write(f"Image size: {image.size}")

    else:
        # Instructions when no file is uploaded
        st.info("👆 Please upload an image file to get started!")

        with st.expander("📋 How to use this tool"):
            st.write("""
            1. **Upload an image**: Use the file uploader above to select your image
            2. **Adjust settings**: Use the sidebar to customize compression settings
            3. **Transparency options**: Choose whether to preserve or replace transparency
            4. **Compress**: Click the compress button to process your image
            5. **Download**: Get both desktop and mobile optimized versions

            **Features:**
            - ✅ Automatic size optimization to meet your target file size
            - ✅ WebP conversion for better compression
            - ✅ **Transparency preservation** for PNG images
            - ✅ Desktop and mobile responsive versions
            - ✅ Quality optimization using binary search algorithm
            - ✅ Support for multiple image formats
            - ✅ Compatible with all Streamlit versions
            """)

        with st.expander("🎭 Transparency Support"):
            st.write("""
            **Supported Transparency Types:**
            - PNG with alpha channel (RGBA)
            - PNG with transparency palette
            - GIF with transparency
            - WebP with transparency

            **How it works:**
            - Original transparency is detected automatically
            - WebP format supports both lossy and lossless transparency
            - You can choose to preserve or replace transparency
            - Transparent areas maintain their transparency in WebP output

            **Benefits:**
            - No more green/white backgrounds on transparent images
            - Smaller file sizes compared to PNG with transparency
            - Perfect for logos, icons, and graphics with transparent backgrounds
            """)

        with st.expander("🎯 Best Practices for Web Images"):
            st.write("""
            **File Size Guidelines:**
            - Hero images: 200-500 KB
            - Content images: 100-300 KB
            - Thumbnails: 10-50 KB
            - Icons: 1-10 KB

            **Dimension Guidelines:**
            - Desktop hero: 1920×1080px or 1366×768px
            - Mobile hero: 768×432px or 375×667px
            - Blog images: 1200×630px
            - Social media: 1200×630px (varies by platform)

            **Format Recommendations:**
            - WebP: Best compression, modern browsers, supports transparency
            - PNG: Best for graphics with transparency (but larger files)
            - JPEG: Good for photos, no transparency support
            """)

    # Display footer
    display_footer()

if __name__ == "__main__":
    main()
