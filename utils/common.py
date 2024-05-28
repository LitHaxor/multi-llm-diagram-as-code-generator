import re

def create_system_prompt(user_prompt, uml_type):
    """create system prompt based on the UML type"""
    sys_inst = generate_promot_by_UML_type(uml_type)
    return f"""
    <system> 
        {sys_inst}
    </system>

    <user>
        <inst>
        {user_prompt}
        </inst>
    </user>
    """

def generate_promot_by_UML_type(uml_type):
    if uml_type == 'flowchart':
        return """
            <inst>
                You're diagram as code generator, you will generate diagram as code using mermaid.js an example code to generate a flowchart diagram is  
                ```
                flowchart TB
                A[Start] --Some text--> B(Continue)
                B --> C{Evaluate}
                C -- One --> D[Option 1]
                C -- Two --> E[Option 2]
                C -- Three --> F[fa:fa-car Option 3]
                ```
            </inst>
        """
    
    if uml_type == 'sequence':
        return """
            <inst>
                You're diagram as code generator, you will generate diagram as code using mermaid.js an example code to generate a sequence diagram is  
                ```
                sequenceDiagram
                Alice->>John: Hello John, how are you?
                John-->>Alice: Great!
                ```
            </inst>
        """
    
    if uml_type == 'class':
        return """
            <inst>
                You're diagram as code generator, you will generate diagram as code using mermaid.js an example code to generate a class diagram is  
                ```
                classDiagram
                Class01 <|-- AveryLongClass : Cool
                Class03 *-- Class04
                Class05 o-- Class06
                Class07 .. Class08
                Class09 --> C2 : Where am i?
                Class09 --* C3
                Class09 --|> Class07
                Class07 : equals()
                Class07 : Object[] elementData
                Class01 : size()
                Class01 : int chimp
                Class01 : int gorilla
                Class08 <--> C2: Cool label
                ```
            </inst>
        """
    
    if uml_type == 'state':

        return """
            <inst>
                You're diagram as code generator, you will generate diagram as code using mermaid.js an example code to generate a state diagram is  
                ```
                stateDiagram
                [*] --> Still
                Still --> [*]
                Still --> Moving
                Moving --> Still
                Moving --> Crash
                Crash --> [*]
                ```
            </inst>
        """
    
    if uml_type == 'er':
        return """
            <inst>
                You're diagram as code generator, you will generate diagram as code using mermaid.js an example code to generate a ER diagram is  
                ```
                erDiagram
                CUSTOMER ||--o{ ORDER : places
                ORDER ||--|{ LINE-ITEM : contains
                CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
                ```
            </inst>
        """

def santise_markdown_text(text):
    if text.startswith('```mermaid'):
        marmaid_pattern = re.compile(r'```mermaid.*?\n(.*?)```', re.DOTALL)
        return marmaid_pattern.findall(text)[0]

    # also ```mermaid
    
    code_block_pattern = re.compile(r'```.*?\n(.*?)```', re.DOTALL)
    # Find all matches
    code_blocks = code_block_pattern.findall(text)

    
    return code_blocks[0]
        
        
