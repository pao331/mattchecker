import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter as report_letter  # Import with alias
from reportlab.lib.units import inch

def create_bubble_sheet(filename, num_questions=20, title=None):
    """
    Create a bubble sheet template PDF with the specified number of questions.
    
    Args:
        filename (str): Output filename
        num_questions (int): Number of questions to include
        title (str, optional): Title for the template. If None, uses default based on question count.
    """
    c = canvas.Canvas(filename, pagesize=report_letter)
    width, height = report_letter
    
    # Set default title if not specified
    if title is None:
        title = f"MattChecker {num_questions}-Question Answer Sheet"
    
    # Configuration based on number of questions
    questions_per_page = 40
    questions_per_column = 20
    columns_per_page = 2
    rows_per_column = 20
    
    # Calculate number of pages needed
    total_pages = (num_questions + questions_per_page - 1) // questions_per_page
    
    # Process each page
    current_question = 1
    
    for page in range(total_pages):
        # Title and header (on each page)
        c.setFont("Helvetica-Bold", 16)
        if page == 0:
            c.drawCentredString(width/2, height - 0.75*inch, title)
        else:
            c.drawCentredString(width/2, height - 0.75*inch, f"{title} - Page {page+1}")
        
        c.setFont("Helvetica", 12)
        c.drawCentredString(width/2, height - 1.1*inch, "Fill in the bubble corresponding to your answer for each question")
        
        # Student information (only on first page)
        if page == 0:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, height - 1.5*inch, "Name: ________________________________")
            c.drawString(width - 4*inch, height - 1.5*inch, "ID: ___________________")
            
            # Start questions a bit lower on first page to accommodate header
            start_y = height - 2.2*inch
        else:
            # Start questions higher on subsequent pages
            start_y = height - 1.5*inch
        
        # Calculate questions for this page
        questions_this_page = min(questions_per_page, num_questions - (page * questions_per_page))
        
        # Draw columns of questions
        for col in range(columns_per_page):
            # Skip if we've processed all questions for this page
            col_questions = min(questions_per_column, questions_this_page - (col * questions_per_column))
            if col_questions <= 0:
                continue
                
            col_x = 1.0*inch + col * ((width - 2*inch) / columns_per_page)
            
            # Draw questions for this column
            for i in range(col_questions):
                q_num = current_question
                current_question += 1
                
                y = start_y - (i * 0.4*inch)
                
                if y < 0.75*inch:  # If we're too close to bottom of page
                    # This shouldn't happen with our calculations, but just in case
                    break
                
                # Question number
                c.setFont("Helvetica-Bold", 11)
                c.drawString(col_x, y, f"{q_num}.")
                
                # Answer bubbles
                bubble_x = col_x + 0.3*inch
                c.setFont("Helvetica", 10)
                for j, letter in enumerate(["A", "B", "C", "D", "E"]):
                    c.circle(bubble_x + j*0.25*inch, y, 6, stroke=1, fill=0)
                    c.drawString(bubble_x + j*0.25*inch - 3, y - 3, letter)
        
        # Add page number at bottom
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 0.3*inch, f"Page {page+1} of {total_pages}")
        
        # Add a new page for the next iteration, but not after the last page
        if page < total_pages - 1:
            c.showPage()
    
    # Save the PDF
    c.save()
    print(f"Created {filename} with {num_questions} questions")

def main():
    # Ensure the output directory exists
    output_dir = "static/templates"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create templates
    create_bubble_sheet(f"{output_dir}/standard_20.pdf", 20, "Standard 20-Question Answer Sheet")
    create_bubble_sheet(f"{output_dir}/extended_50.pdf", 50, "Extended 50-Question Answer Sheet")
    create_bubble_sheet(f"{output_dir}/comprehensive_100.pdf", 100, "Comprehensive 100-Question Answer Sheet")

if __name__ == "__main__":
    main()